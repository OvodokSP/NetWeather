package com.netweather.domain.usecase

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import com.netweather.domain.repository.DiagnosticsRepository
import javax.inject.Inject

/**
 * Use case для проверки одного ресурса
 */
class CheckResourceUseCase @Inject constructor(
    private val diagnosticsRepository: DiagnosticsRepository
) {
    
    /**
     * Выполнение проверки ресурса
     */
    suspend operator fun invoke(resource: Resource): Result<CheckResult> {
        return try {
            if (!resource.isValidUrl()) {
                return Result.failure(IllegalArgumentException("Некорректный URL ресурса"))
            }
            
            val checkResult = diagnosticsRepository.checkResource(resource)
            diagnosticsRepository.saveCheckResult(checkResult)
            
            Result.success(checkResult)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Быстрая проверка доступности ресурса
     */
    suspend fun checkAvailability(resource: Resource): Result<Boolean> {
        return try {
            val isAvailable = diagnosticsRepository.isResourceAvailable(resource)
            Result.success(isAvailable)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}