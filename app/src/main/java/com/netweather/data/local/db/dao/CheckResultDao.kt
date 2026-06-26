package com.netweather.data.local.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.netweather.data.local.db.entity.CheckResultEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CheckResultDao {
    
    @Query("""
        SELECT * FROM check_results 
        WHERE resource_id = :resourceId 
        ORDER BY timestamp DESC 
        LIMIT 1
    """)
    suspend fun getLastCheckResult(resourceId: Long): CheckResultEntity?
    
    @Query("""
        SELECT cr.* FROM check_results cr
        INNER JOIN (
            SELECT resource_id, MAX(timestamp) as max_timestamp
            FROM check_results
            GROUP BY resource_id
        ) latest ON cr.resource_id = latest.resource_id 
                 AND cr.timestamp = latest.max_timestamp
        ORDER BY cr.timestamp DESC
    """)
    fun getLastCheckResults(): Flow<List<CheckResultEntity>>
    
    @Query("""
        SELECT cr.* FROM check_results cr
        INNER JOIN (
            SELECT resource_id, MAX(timestamp) as max_timestamp
            FROM check_results
            GROUP BY resource_id
        ) latest ON cr.resource_id = latest.resource_id 
                 AND cr.timestamp = latest.max_timestamp
        ORDER BY cr.timestamp DESC
    """)
    suspend fun getLastCheckResultsOnce(): List<CheckResultEntity>
    
    @Query("""
        SELECT * FROM check_results 
        WHERE resource_id = :resourceId 
        ORDER BY timestamp DESC 
        LIMIT :limit
    """)
    suspend fun getCheckHistory(resourceId: Long, limit: Int = 100): List<CheckResultEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCheckResult(checkResult: CheckResultEntity): Long
    
    @Query("DELETE FROM check_results WHERE timestamp < :olderThan")
    suspend fun deleteOldCheckResults(olderThan: Long): Int
    
    @Query("DELETE FROM check_results")
    suspend fun deleteAllCheckResults()
    
    @Query("""
        SELECT AVG(response_time_ms) FROM check_results 
        WHERE resource_id = :resourceId 
        AND timestamp > :sinceTimestamp
    """)
    suspend fun getAverageResponseTime(resourceId: Long, sinceTimestamp: Long): Long?
}