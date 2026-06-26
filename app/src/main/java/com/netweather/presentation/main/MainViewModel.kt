package com.netweather.presentation.main

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.NetworkState
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.ResourceState
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.usecase.CalculateAvailabilityIndexUseCase
import com.netweather.domain.usecase.CheckAllResourcesUseCase
import com.netweather.domain.usecase.DetermineNetworkModeUseCase
import com.netweather.widget.WidgetUtils
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val checkAllResourcesUseCase: CheckAllResourcesUseCase,
    private val calculateAvailabilityIndexUseCase: CalculateAvailabilityIndexUseCase,
    private val determineNetworkModeUseCase: DetermineNetworkModeUseCase,
    @ApplicationContext private val appContext: Context
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(MainUiState())
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()
    
    init {
        observeResources()
        refreshData()
    }
    
    private fun observeResources() {
        viewModelScope.launch {
            resourceRepository.getAllResources().collect { resources ->
                updateResourceStates(resources)
            }
        }
    }
    
    fun refreshData() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                error = null
            )
            
            try {
                val checkResult = checkAllResourcesUseCase.checkAllOnce()
                
                if (checkResult.isFailure) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = checkResult.exceptionOrNull()?.message ?: "Ошибка проверки"
                    )
                    return@launch
                }
                
                val checkResults = checkResult.getOrDefault(emptyList())
                val resources = resourceRepository.getAllResourcesOnce()
                
                val indexResult = calculateAvailabilityIndexUseCase(resources, checkResults)
                val availabilityIndex = if (indexResult.isSuccess) {
                    indexResult.getOrNull() ?: AvailabilityIndex.create(0)
                } else {
                    AvailabilityIndex.create(0)
                }
                
                val modeResult = determineNetworkModeUseCase(availabilityIndex, resources, checkResults)
                val networkMode = if (modeResult.isSuccess) {
                    modeResult.getOrNull() ?: NetworkMode.NO_INTERNET
                } else {
                    NetworkMode.NO_INTERNET
                }
                
                val availableCount = checkResults.count { it.isSuccessful() }
                val unavailableCount = checkResults.size - availableCount
                
                val resourceStates = createResourceStates(resources, checkResults)
                
                val networkState = NetworkState(
                    availabilityIndex = availabilityIndex,
                    networkMode = networkMode,
                    lastCheckTime = System.currentTimeMillis(),
                    availableCount = availableCount,
                    unavailableCount = unavailableCount,
                    totalResources = resources.size,
                    resourceStates = resourceStates
                )
                
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    networkState = networkState,
                    error = null
                )
                WidgetUtils.updateAllWidgets(appContext, networkState)
                
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Неизвестная ошибка"
                )
            }
        }
    }
    
    private suspend fun updateResourceStates(resources: List<Resource>) {
        val checkResults = diagnosticsRepository.getLastCheckResultsOnce()
        val resourceStates = createResourceStates(resources, checkResults)
        
        val currentState = _uiState.value.networkState
        if (currentState != null) {
            _uiState.value = _uiState.value.copy(
                networkState = currentState.copy(resourceStates = resourceStates)
            )
        }
    }
    
    private fun createResourceStates(
        resources: List<Resource>,
        checkResults: List<CheckResult>
    ): Map<ResourceGroup, List<ResourceState>> {
        val resultsMap = checkResults.associateBy { it.resourceId }
        
        return resources.groupBy { it.group }.mapValues { (_, groupResources) ->
            groupResources.map { resource ->
                val checkResult = resultsMap[resource.id]
                ResourceState(
                    resource = resource,
                    lastCheckResult = checkResult,
                    isAvailable = checkResult?.isSuccessful() == true,
                    responseTimeMs = checkResult?.responseTimeMs ?: 0,
                    lastCheckTime = checkResult?.timestamp ?: 0
                )
            }.sortedBy { it.resource.name }
        }
    }
    
    fun toggleResource(resourceId: Long) {
        viewModelScope.launch {
            val resource = resourceRepository.getResourceById(resourceId) ?: return@launch
            resourceRepository.setResourceEnabled(resourceId, !resource.enabled)
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

data class MainUiState(
    val isLoading: Boolean = false,
    val networkState: NetworkState? = null,
    val error: String? = null
) {
    fun hasData(): Boolean = networkState != null
    fun hasError(): Boolean = error != null
}