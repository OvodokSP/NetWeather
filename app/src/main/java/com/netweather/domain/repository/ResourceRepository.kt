package com.netweather.domain.repository

import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import kotlinx.coroutines.flow.Flow

/**
 * Интерфейс репозитория для управления ресурсами
 */
interface ResourceRepository {
    
    fun getAllResources(): Flow<List<Resource>>
    
    fun getResourcesByGroup(group: ResourceGroup): Flow<List<Resource>>
    
    fun getEnabledResources(): Flow<List<Resource>>
    
    suspend fun getResourceById(id: Long): Resource?
    
    suspend fun addResource(resource: Resource): Long
    
    suspend fun updateResource(resource: Resource)
    
    suspend fun deleteResource(id: Long)
    
    suspend fun setResourceEnabled(id: Long, enabled: Boolean)
    
    suspend fun resourceExists(url: String): Boolean
    
    suspend fun getResourceCount(group: ResourceGroup): Int
    
    suspend fun getTotalResourceCount(): Int
    
    suspend fun initializeDefaultResources()
    
    suspend fun deleteAllResources()
    
    suspend fun getAllResourcesOnce(): List<Resource>
}