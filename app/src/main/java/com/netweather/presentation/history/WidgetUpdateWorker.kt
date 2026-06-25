package com.netweather.widget

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.NetworkState
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.ResourceState
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.usecase.CalculateAvailabilityIndexUseCase
import com.netweather.domain.usecase.DetermineNetworkModeUseCase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import java.util.concurrent.TimeUnit

/**
 * Worker для периодического обновления виджетов
 * Выполняет проверку ресурсов и обновляет UI виджетов
 */
@HiltWorker
class WidgetUpdateWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val calculateAvailabilityIndexUseCase: CalculateAvailabilityIndexUseCase,
    private val determineNetworkModeUseCase: DetermineNetworkModeUseCase
) : CoroutineWorker(context, workerParams) {
    
    override suspend fun doWork(): Result {
        return try {
            val resources = resourceRepository.getAllResourcesOnce().filter { it.enabled }
            
            if (resources.isEmpty()) {
                WidgetUtils.updateAllWidgets(applicationContext, null)
                return Result.success()
            }
            
            // Параллельная проверка ресурсов
            val checkResults = coroutineScope {
                resources.map { resource ->
                    async {
                        try {
                            val result = diagnosticsRepository.checkResource(resource)
                            diagnosticsRepository.saveCheckResult(result)
                            result
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
            
            // Расчёт состояния
            val indexResult = calculateAvailabilityIndexUseCase(resources, checkResults)
            val availabilityIndex = indexResult.getOrNull() ?: AvailabilityIndex.create(0)
            
            val modeResult = determineNetworkModeUseCase(availabilityIndex, resources, checkResults)
            val networkMode = modeResult.getOrNull() ?: NetworkMode.NO_INTERNET
            
            val availableCount = checkResults.count { it.isSuccessful() }
            val unavailableCount = checkResults.size - availableCount
            
            val resultsMap = checkResults.associateBy { it.resourceId }
            val resourceStates = resources.groupBy { it.group }.mapValues { (_, groupResources) ->
                groupResources.map { resource ->
                    val checkResult = resultsMap[resource.id]
                    ResourceState(
                        resource = resource,
                        lastCheckResult = checkResult,
                        isAvailable = checkResult?.isSuccessful() == true,
                        responseTimeMs = checkResult?.responseTimeMs ?: 0,
                        lastCheckTime = checkResult?.timestamp ?: 0
                    )
                }
            }
            
            val networkState = NetworkState(
                availabilityIndex = availabilityIndex,
                networkMode = networkMode,
                lastCheckTime = System.currentTimeMillis(),
                availableCount = availableCount,
                unavailableCount = unavailableCount,
                totalResources = resources.size,
                resourceStates = resourceStates
            )
            
            // Обновление виджетов
            WidgetUtils.updateAllWidgets(applicationContext, networkState)
            
            Result.success()
        } catch (e: Exception) {
            e.printStackTrace()
            Result.retry()
        }
    }
    
    companion object {
        private const val WORK_NAME = "widget_update_worker"
        
        /**
         * Запуск периодического обновления (раз в 30 минут)
         */
        fun enqueuePeriodicUpdate(context: Context) {
            val workRequest = PeriodicWorkRequestBuilder<WidgetUpdateWorker>(
                30, TimeUnit.MINUTES
            ).build()
            
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                workRequest
            )
        }
        
        /**
         * Отмена периодического обновления
         */
        fun cancelPeriodicUpdate(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
        
        /**
         * Немедленное однократное обновление
         */
        fun enqueueUpdate(context: Context) {
            val workRequest = androidx.work.OneTimeWorkRequestBuilder<WidgetUpdateWorker>().build()
            WorkManager.getInstance(context).enqueue(workRequest)
        }
    }
}