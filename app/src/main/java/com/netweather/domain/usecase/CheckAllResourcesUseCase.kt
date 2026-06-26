package com.netweather.domain.usecase

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus
import com.netweather.domain.model.Resource
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.ResourceRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import javax.inject.Inject

/**
 * Use case для проверки всех ресурсов
 */
class CheckAllResourcesUseCase @Inject constructor(
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository
) {
    
    /**
     * Выполнение проверки всех включённых ресурсов
     */
    suspend operator fun invoke(): Result<List<CheckResult>> {
        return try {
            val resources = resourceRepository.getAllResourcesOnce()
                .filter { it.enabled }
            
            if (resources.isEmpty()) {
                return Result.success(emptyList())
            }
            
            val checkResults = coroutineScope {
                resources.map { resource ->
                    async {
                        try {
                            val checkResult = diagnosticsRepository.checkResource(resource)
                            diagnosticsRepository.saveCheckResult(checkResult)
                            checkResult
                        } catch (e: Exception) {
                            CheckResult(
                                resourceId = resource.id,
                                dnsStatus = DiagnosticStatus.UNKNOWN_ERROR,
                                tcpStatus = DiagnosticStatus.UNKNOWN_ERROR,
                                tlsStatus = DiagnosticStatus.UNKNOWN_ERROR,
                                httpStatus = DiagnosticStatus.UNKNOWN_ERROR,
                                contentStatus = DiagnosticStatus.UNKNOWN_ERROR,
                                responseTimeMs = 0,
                                errorMessage = e.message
                            )
                        }
                    }
                }.awaitAll()
            }
            
            Result.success(checkResults)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Выполнение проверки всех ресурсов (suspend версия без Flow)
     */
    suspend fun checkAllOnce(): Result<List<CheckResult>> {
        return invoke()
    }
}