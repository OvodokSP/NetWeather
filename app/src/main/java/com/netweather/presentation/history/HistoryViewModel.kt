package com.netweather.presentation.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.domain.repository.HistoryRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(
    private val historyRepository: HistoryRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(HistoryUiState())
    val uiState: StateFlow<HistoryUiState> = _uiState.asStateFlow()
    
    private val _selectedPeriod = MutableStateFlow(HistoryPeriod.DAY)
    val selectedPeriod: StateFlow<HistoryPeriod> = _selectedPeriod.asStateFlow()
    
    init {
        loadHistory()
    }
    
    fun loadHistory() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                val period = _selectedPeriod.value
                val history = historyRepository.getHistoryOnce(period)
                val statistics = historyRepository.getStatistics(period)
                val averageIndex = historyRepository.getAverageAvailabilityIndex(period)
                val minIndex = historyRepository.getMinAvailabilityIndex(period)
                val maxIndex = historyRepository.getMaxAvailabilityIndex(period)
                
                val stats = HistoryStatistics(
                    averageIndex = averageIndex,
                    minIndex = minIndex,
                    maxIndex = maxIndex,
                    totalEntries = history.size,
                    normalCount = statistics["normalCount"] as? Int ?: 0,
                    partialCount = statistics["partialCount"] as? Int ?: 0,
                    restrictedCount = statistics["restrictedCount"] as? Int ?: 0,
                    noInternetCount = statistics["noInternetCount"] as? Int ?: 0
                )
                
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    historyEntries = history,
                    statistics = stats,
                    error = null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Ошибка загрузки истории"
                )
            }
        }
    }
    
    fun selectPeriod(period: HistoryPeriod) {
        _selectedPeriod.value = period
        loadHistory()
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

data class HistoryUiState(
    val isLoading: Boolean = false,
    val historyEntries: List<HistoryEntry> = emptyList(),
    val statistics: HistoryStatistics? = null,
    val error: String? = null
) {
    fun hasData(): Boolean = historyEntries.isNotEmpty()
    fun hasError(): Boolean = error != null
}

data class HistoryStatistics(
    val averageIndex: Int,
    val minIndex: Int,
    val maxIndex: Int,
    val totalEntries: Int,
    val normalCount: Int,
    val partialCount: Int,
    val restrictedCount: Int,
    val noInternetCount: Int
) {
    fun getModePercentages(): Map<String, Int> {
        if (totalEntries == 0) {
            return mapOf("normal" to 0, "partial" to 0, "restricted" to 0, "noInternet" to 0)
        }
        return mapOf(
            "normal" to (normalCount * 100) / totalEntries,
            "partial" to (partialCount * 100) / totalEntries,
            "restricted" to (restrictedCount * 100) / totalEntries,
            "noInternet" to (noInternetCount * 100) / totalEntries
        )
    }
}