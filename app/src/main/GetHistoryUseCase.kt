package com.netweather.domain.usecase

import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.domain.repository.HistoryRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

/**
 * Use case для получения истории состояния сети
 */
class GetHistoryUseCase @Inject constructor(
    private val historyRepository: HistoryRepository
) {
    
    /**
     * Получение истории за указанный период как Flow
     */
    operator fun invoke(period: HistoryPeriod): Flow<List<HistoryEntry>> {
        return historyRepository.getHistory(period)
    }
    
    /**
     * Получение истории за указанный период
     */
    suspend fun getOnce(period: HistoryPeriod): Result<List<HistoryEntry>> {
        return try {
            val history = historyRepository.getHistoryOnce(period)
            Result.success(history)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Получение последней записи истории
     */
    suspend fun getLast(): Result<HistoryEntry?> {
        return try {
            val lastEntry = historyRepository.getLastHistoryEntry()
            Result.success(lastEntry)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Получение статистики за период
     */
    suspend fun getStatistics(period: HistoryPeriod): Result<Map<String, Any>> {
        return try {
            val statistics = historyRepository.getStatistics(period)
            Result.success(statistics)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Получение среднего индекса доступности за период
     */
    suspend fun getAverageIndex(period: HistoryPeriod): Result<Int> {
        return try {
            val average = historyRepository.getAverageAvailabilityIndex(period)
            Result.success(average)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}