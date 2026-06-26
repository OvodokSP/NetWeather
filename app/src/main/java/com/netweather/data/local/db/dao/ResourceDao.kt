package com.netweather.data.local.db.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.netweather.data.local.db.entity.ResourceEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ResourceDao {
    
    @Query("SELECT * FROM resources ORDER BY created_at DESC")
    fun getAllResources(): Flow<List<ResourceEntity>>
    
    @Query("SELECT * FROM resources ORDER BY created_at DESC")
    suspend fun getAllResourcesOnce(): List<ResourceEntity>
    
    @Query("SELECT * FROM resources WHERE `group` = :group ORDER BY name ASC")
    fun getResourcesByGroup(group: String): Flow<List<ResourceEntity>>
    
    @Query("SELECT * FROM resources WHERE enabled = 1 ORDER BY `group`, name ASC")
    fun getEnabledResources(): Flow<List<ResourceEntity>>
    
    @Query("SELECT * FROM resources WHERE id = :id LIMIT 1")
    suspend fun getResourceById(id: Long): ResourceEntity?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertResource(resource: ResourceEntity): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertResources(resources: List<ResourceEntity>): List<Long>
    
    @Update
    suspend fun updateResource(resource: ResourceEntity)
    
    @Query("DELETE FROM resources WHERE id = :id")
    suspend fun deleteResourceById(id: Long)
    
    @Query("UPDATE resources SET enabled = :enabled WHERE id = :id")
    suspend fun setResourceEnabled(id: Long, enabled: Boolean)
    
    @Query("SELECT EXISTS(SELECT 1 FROM resources WHERE url = :url)")
    suspend fun resourceExists(url: String): Boolean
    
    @Query("SELECT COUNT(*) FROM resources WHERE `group` = :group")
    suspend fun getResourceCount(group: String): Int
    
    @Query("SELECT COUNT(*) FROM resources")
    suspend fun getTotalResourceCount(): Int
    
    @Query("DELETE FROM resources")
    suspend fun deleteAllResources()
}