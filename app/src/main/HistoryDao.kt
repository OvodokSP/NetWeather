package com.netweather.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.netweather.data.local.db.entity.HistoryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface HistoryDao {
    
    @Query("SELECT * FROM history WHERE timestamp > :sinceTimestamp ORDER BY timestamp DESC")
    fun getHistorySince(sinceTimestamp: Long): Flow<List<HistoryEntity>>
    
    @Query("SELECT * FROM history WHERE timestamp > :sinceTimestamp ORDER BY timestamp DESC")
    suspend fun getHistorySinceOnce(sinceTimestamp: Long): List<HistoryEntity>
    
    @Query("SELECT * FROM history ORDER BY timestamp DESC LIMIT 1")
    suspend fun getLastHistoryEntry(): HistoryEntity?
    
    @Query("SELECT * FROM history WHERE id = :id LIMIT 1")
    suspend fun getHistoryEntryById(id: Long): HistoryEntity?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertHistoryEntry(historyEntry: HistoryEntity): Long
    
    @Query("DELETE FROM history WHERE timestamp < :olderThan")
    suspend fun deleteOldHistory(olderThan: Long): Int
    
    @Query("DELETE FROM history")
    suspend fun deleteAllHistory()
    
    @Query("SELECT COUNT(*) FROM history")
    suspend fun getHistoryCount(): Int
    
    @Query("""
        SELECT AVG(availability_index) FROM history 
        WHERE timestamp > :sinceTimestamp
    """)
    suspend fun getAverageAvailabilityIndex(sinceTimestamp: Long): Int?
    
    @Query("""
        SELECT MIN(availability_index) FROM history 
        WHERE timestamp > :sinceTimestamp
    """)
    suspend fun getMinAvailabilityIndex(sinceTimestamp: Long): Int?
    
    @Query("""
        SELECT MAX(availability_index) FROM history 
        WHERE timestamp > :sinceTimestamp
    """)
    suspend fun getMaxAvailabilityIndex(sinceTimestamp: Long): Int?
    
    @Query("""
        SELECT COUNT(*) FROM history 
        WHERE network_mode = :networkMode 
        AND timestamp > :sinceTimestamp
    """)
    suspend fun getCountByNetworkMode(networkMode: String, sinceTimestamp: Long): Int
}