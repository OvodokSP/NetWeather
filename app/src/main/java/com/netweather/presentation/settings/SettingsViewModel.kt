package com.netweather.presentation.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import com.netweather.domain.usecase.AddResourceUseCase
import com.netweather.domain.usecase.DeleteResourceUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val resourceRepository: ResourceRepository,
    private val addResourceUseCase: AddResourceUseCase,
    private val deleteResourceUseCase: DeleteResourceUseCase
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()
    
    init {
        observeSettings()
        observeResources()
    }
    
    private fun observeSettings() {
        viewModelScope.launch {
            settingsRepository.getSettings().collect { settings ->
                _uiState.value = _uiState.value.copy(
                    settings = settings,
                    isLoading = false
                )
            }
        }
    }
    
    private fun observeResources() {
        viewModelScope.launch {
            resourceRepository.getAllResources().collect { resources ->
                _uiState.value = _uiState.value.copy(
                    resources = resources,
                    russianResources = resources.filter { it.group == ResourceGroup.RU },
                    internationalResources = resources.filter { it.group == ResourceGroup.INTL },
                    customResources = resources.filter { it.group == ResourceGroup.CUSTOM }
                )
            }
        }
    }
    
    fun setThemeMode(themeMode: ThemeMode) {
        viewModelScope.launch {
            try {
                settingsRepository.setThemeMode(themeMode)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения темы: ${e.message}"
                )
            }
        }
    }
    
    fun setCheckInterval(minutes: Int) {
        viewModelScope.launch {
            try {
                settingsRepository.setCheckInterval(minutes)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения интервала: ${e.message}"
                )
            }
        }
    }
    
    fun setConnectionTimeout(timeoutMs: Long) {
        viewModelScope.launch {
            try {
                settingsRepository.setConnectionTimeout(timeoutMs)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения таймаута: ${e.message}"
                )
            }
        }
    }
    
    fun setNotificationsEnabled(enabled: Boolean) {
        viewModelScope.launch {
            try {
                settingsRepository.setNotificationsEnabled(enabled)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения настроек уведомлений: ${e.message}"
                )
            }
        }
    }
    
    fun setNotifyOnFailure(enabled: Boolean) {
        viewModelScope.launch {
            try {
                settingsRepository.setNotifyOnFailure(enabled)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения настроек: ${e.message}"
                )
            }
        }
    }
    
    fun setNotifyOnRecovery(enabled: Boolean) {
        viewModelScope.launch {
            try {
                settingsRepository.setNotifyOnRecovery(enabled)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения настроек: ${e.message}"
                )
            }
        }
    }
    
    fun setNotifyOnSlowResponse(enabled: Boolean) {
        viewModelScope.launch {
            try {
                settingsRepository.setNotifyOnSlowResponse(enabled)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения настроек: ${e.message}"
                )
            }
        }
    }
    
    fun setSlowResponseThreshold(thresholdMs: Long) {
        viewModelScope.launch {
            try {
                settingsRepository.setSlowResponseThreshold(thresholdMs)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения порога: ${e.message}"
                )
            }
        }
    }
    
    fun setHistoryRetentionDays(days: Int) {
        viewModelScope.launch {
            try {
                settingsRepository.setHistoryRetentionDays(days)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения настроек истории: ${e.message}"
                )
            }
        }
    }
    
    fun addCustomResource(name: String, url: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            try {
                val result = addResourceUseCase(name, url, ResourceGroup.CUSTOM)
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Ресурс добавлен"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Ошибка добавления ресурса"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Ошибка добавления ресурса"
                )
            }
        }
    }
    
    fun deleteResource(resourceId: Long) {
        viewModelScope.launch {
            try {
                val result = deleteResourceUseCase(resourceId)
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        successMessage = "Ресурс удалён"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        error = result.exceptionOrNull()?.message ?: "Ошибка удаления ресурса"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = e.message ?: "Ошибка удаления ресурса"
                )
            }
        }
    }
    
    fun toggleResource(resourceId: Long) {
        viewModelScope.launch {
            try {
                val resource = resourceRepository.getResourceById(resourceId) ?: return@launch
                resourceRepository.setResourceEnabled(resourceId, !resource.enabled)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Ошибка изменения состояния ресурса: ${e.message}"
                )
            }
        }
    }
    
    fun resetSettings() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            
            try {
                settingsRepository.resetToDefaults()
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    successMessage = "Настройки сброшены"
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Ошибка сброса настроек: ${e.message}"
                )
            }
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
    
    fun clearSuccessMessage() {
        _uiState.value = _uiState.value.copy(successMessage = null)
    }
}

data class SettingsUiState(
    val isLoading: Boolean = false,
    val settings: Settings = Settings(),
    val resources: List<Resource> = emptyList(),
    val russianResources: List<Resource> = emptyList(),
    val internationalResources: List<Resource> = emptyList(),
    val customResources: List<Resource> = emptyList(),
    val error: String? = null,
    val successMessage: String? = null
) {
    fun hasError(): Boolean = error != null
    fun hasSuccessMessage(): Boolean = successMessage != null
}