package com.netweather.domain.usecase

import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.repository.ResourceRepository
import javax.inject.Inject

/**
 * Use case для удаления ресурса
 */
class DeleteResourceUseCase @Inject constructor(
    private val resourceRepository: ResourceRepository
) {
    
    /**
     * Удаление ресурса по ID
     */
    suspend operator fun invoke(id: Long): Result<Unit> {
        return try {
            val resource = resourceRepository.getResourceById(id)
            if (resource == null) {
                return Result.failure(NoSuchElementException("Ресурс не найден"))
            }
            
            resourceRepository.deleteResource(id)
            
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Удаление всех пользовательских ресурсов
     */
    suspend fun deleteAllCustomResources(): Result<Int> {
        return try {
            val resources = resourceRepository.getAllResourcesOnce()
            val customResources = resources.filter { 
                it.group == ResourceGroup.CUSTOM 
            }
            
            var deletedCount = 0
            customResources.forEach { resource ->
                resourceRepository.deleteResource(resource.id)
                deletedCount++
            }
            
            Result.success(deletedCount)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Удаление всех ресурсов
     */
    suspend fun deleteAllResources(): Result<Unit> {
        return try {
            resourceRepository.deleteAllResources()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}