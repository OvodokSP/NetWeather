package com.netweather.data.repository

import com.netweather.data.local.db.dao.HistoryDao
import com.netweather.data.local.db.entity.HistoryEntity
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.domain.repository.HistoryRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HistoryRepositoryImpl @Inject constructor(
    private val historyDao: HistoryDao
) : HistoryRepository {

    override suspend fun saveHistoryEntry(entry: HistoryEntry): Long = historyDao.insertHistoryEntry(HistoryEntity.fromDomain(entry))
    override fun getHistory(period: HistoryPeriod): Flow<List<HistoryEntry>> = historyDao.getHistorySince(System.currentTimeMillis() - period.getDurationMs()).map { it.map { e -> e.toDomain() } }
    override suspend fun getHistoryOnce(period: HistoryPeriod): List<HistoryEntry> = historyDao.getHistorySinceOnce(System.currentTimeMillis() - period.getDurationMs()).map { it.toDomain() }
    override suspend fun getLastHistoryEntry(): HistoryEntry? = historyDao.getLastHistoryEntry()?.toDomain()
    override suspend fun getHistoryEntryById(id: Long): HistoryEntry? = historyDao.getHistoryEntryById(id)?.toDomain()
    override suspend fun deleteOldHistory(olderThanMs: Long): Int = historyDao.deleteOldHistory(System.currentTimeMillis() - olderThanMs)
    override suspend fun deleteAllHistory() = historyDao.deleteAllHistory()
    override suspend fun getHistoryCount(): Int = historyDao.getHistoryCount()
    override suspend fun getHistoryWithPagination(period: HistoryPeriod, limit: Int, offset: Int): List<HistoryEntry> = emptyList() // Упрощено для MVP
    
    override suspend fun getStatistics(period: HistoryPeriod): Map<String, Any> {
        val since = System.currentTimeMillis() - period.getDurationMs()
        return mapOf(
            "normalCount" to historyDao.getCountByNetworkMode("NORMAL", since),
            "partialCount" to historyDao.getCountByNetworkMode("PARTIAL_DEGRADATION", since),
            "restrictedCount" to historyDao.getCountByNetworkMode("RESTRICTED_ACCESS", since),
            "noInternetCount" to historyDao.getCountByNetworkMode("NO_INTERNET", since)
        )
    }
    
    override suspend fun getAverageAvailabilityIndex(period: HistoryPeriod): Int = historyDao.getAverageAvailabilityIndex(System.currentTimeMillis() - period.getDurationMs()) ?: 0
    override suspend fun getMinAvailabilityIndex(period: HistoryPeriod): Int = historyDao.getMinAvailabilityIndex(System.currentTimeMillis() - period.getDurationMs()) ?: 0
    override suspend fun getMaxAvailabilityIndex(period: HistoryPeriod): Int = historyDao.getMaxAvailabilityIndex(System.currentTimeMillis() - period.getDurationMs()) ?: 0
}