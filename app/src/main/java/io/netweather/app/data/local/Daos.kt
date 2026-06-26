package io.netweather.app.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface ResourceDao {
    @Query("SELECT * FROM resources ORDER BY priority DESC, name ASC") fun observeAll(): Flow<List<ResourceEntity>>
    @Query("SELECT * FROM resources ORDER BY priority DESC, name ASC") suspend fun getAll(): List<ResourceEntity>
    @Query("SELECT * FROM resources WHERE enabled = 1 ORDER BY priority DESC, name ASC") suspend fun getEnabled(): List<ResourceEntity>
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(resource: ResourceEntity): Long
    @Update suspend fun update(resource: ResourceEntity)
    @Delete suspend fun delete(resource: ResourceEntity)
    @Query("UPDATE resources SET enabled = :enabled WHERE id = :id") suspend fun setEnabled(id: Long, enabled: Boolean)
    @Query("SELECT COUNT(*) FROM resources") suspend fun count(): Int
}

@Dao
interface CheckResultDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun insert(result: CheckResultEntity): Long
    @Query("SELECT * FROM check_results WHERE timestamp IN (SELECT MAX(timestamp) FROM check_results GROUP BY resourceId)") suspend fun latest(): List<CheckResultEntity>
    @Query("SELECT * FROM check_results WHERE timestamp >= :from ORDER BY timestamp DESC") fun observeSince(from: Long): Flow<List<CheckResultEntity>>
    @Query("SELECT * FROM check_results WHERE resourceId = :resourceId AND status = 'OK' ORDER BY timestamp DESC LIMIT 1") suspend fun lastSuccess(resourceId: Long): CheckResultEntity?
}

@Dao
interface HistoryDao {
    @Insert suspend fun insert(entry: HistoryEntity): Long
    @Query("SELECT * FROM history WHERE timestamp >= :from ORDER BY timestamp ASC") fun observeSince(from: Long): Flow<List<HistoryEntity>>
    @Query("DELETE FROM history WHERE timestamp < :before") suspend fun deleteBefore(before: Long)
}
