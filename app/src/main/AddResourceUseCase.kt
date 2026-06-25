package com.netweather.domain.usecase

import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.repository.ResourceRepository
import javax.inject.Inject

/**
 * Use case для добавления нового ресурса
 */
class AddResourceUseCase @Inject constructor(
    private val resourceRepository: ResourceRepository
) {
    
    /**
     * Добавление нового ресурса
     */
    suspend operator fun invoke(
        name: String,
        url: String,
        group: ResourceGroup
    ): Result<Long> {
        return try {
            if (name.isBlank()) {
                return Result.failure(IllegalArgumentException("Имя ресурса не может быть пустым"))
            }
            
            val normalizedUrl = normalizeUrl(url)
            if (!isValidUrl(normalizedUrl)) {
                return Result.failure(IllegalArgumentException("Некорректный URL"))
            }
            
            if (resourceRepository.resourceExists(normalizedUrl)) {
                return Result.failure(IllegalStateException("Ресурс с таким URL уже существует"))
            }
            
            val resource = Resource(
                name = name.trim(),
                url = normalizedUrl,
                group = group,
                enabled = true,
                createdAt = System.currentTimeMillis()
            )
            
            val id = resourceRepository.addResource(resource)
            
            Result.success(id)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Добавление ресурса из объекта Resource
     */
    suspend fun addResource(resource: Resource): Result<Long> {
        return try {
            if (resource.name.isBlank()) {
                return Result.failure(IllegalArgumentException("Имя ресурса не может быть пустым"))
            }
            
            if (!resource.isValidUrl()) {
                return Result.failure(IllegalArgumentException("Некорректный URL"))
            }
            
            if (resourceRepository.resourceExists(resource.url)) {
                return Result.failure(IllegalStateException("Ресурс с таким URL уже существует"))
            }
            
            val id = resourceRepository.addResource(resource)
            Result.success(id)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Нормализация URL
     */
    private fun normalizeUrl(url: String): String {
        var normalized = url.trim()
        
        if (!normalized.startsWith("http://") && !normalized.startsWith("https://")) {
            normalized = "https://$normalized"
        }
        
        if (normalized.endsWith("/") && normalized.count { it == '/' } == 3) {
            normalized = normalized.dropLast(1)
        }
        
        return normalized.lowercase()
    }
    
    /**
     * Проверка валидности URL
     */
    private fun isValidUrl(url: String): Boolean {
        return try {
            val urlObj = java.net.URL(url)
            urlObj.host.isNotBlank()
        } catch (e: Exception) {
            false
        }
    }
}