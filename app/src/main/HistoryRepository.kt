package com.netweather.domain.repository

import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import kotlinx.coroutines.flow.Flow

/**
 * Интерфейс репозитория для работы с историей состояния сети
 */
interface HistoryRepository {
    
    suspend fun saveHistoryEntry(entry: HistoryEntry): Long
    
    fun getHistory(period: HistoryPeriod): Flow<List<HistoryEntry>>
    
    suspend fun getHistoryOnce(period: HistoryPeriod): List<HistoryEntry>
    
    suspend fun getLastHistoryEntry(): HistoryEntry?
    
    suspend fun getHistoryEntryById(id: Long): HistoryEntry?
    
    suspend fun deleteOldHistory(olderThanMs: Long): Int
    
    suspend fun deleteAllHistory()
    
    suspend fun getHistoryCount(): Int
    
    suspend fun getHistoryWithPagination(
        period: HistoryPeriod,
        limit: Int,
        offset: Int = 0
    ): List<HistoryEntry>
    
    suspend fun getStatistics(period: HistoryPeriod): Map<String, Any>
    
    suspend fun getAverageAvailabilityIndex(period: HistoryPeriod): Int
    
    suspend fun getMinAvailabilityIndex(period: HistoryPeriod): Int
    
    suspend fun getMaxAvailabilityIndex(period: HistoryPeriod): Int
}