package com.netweather.worker

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
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.NetworkState
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.ResourceState
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.HistoryRepository
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import com.netweather.domain.usecase.CalculateAvailabilityIndexUseCase
import com.netweather.domain.usecase.DetermineNetworkModeUseCase
import com.netweather.notification.NotificationManager
import com.netweather.widget.WidgetUtils
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import java.util.concurrent.TimeUnit

/**
 * Главный фоновый Worker для периодической проверки сети
 */
@HiltWorker
class PeriodicCheckWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val historyRepository: HistoryRepository,
    private val settingsRepository: SettingsRepository,
    private val calculateAvailabilityIndexUseCase: CalculateAvailabilityIndexUseCase,
    private val determineNetworkModeUseCase: DetermineNetworkModeUseCase,
    private val notificationManager: NotificationManager
) : CoroutineWorker(context, workerParams) {
    
    override suspend fun doWork(): Result {
        return try {
            val settings = settingsRepository.getSettingsOnce()
            val resources = resourceRepository.getAllResourcesOnce().filter { it.enabled }
            
            if (resources.isEmpty()) {
                return Result.success()
            }
            
            // Получаем предыдущие результаты для сравнения (уведомления)
            val previousResults = diagnosticsRepository.getLastCheckResultsOnce()
                .associateBy { it.resourceId }
            
            // Параллельная проверка
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
            
            // Расчёт индекса и режима
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
            
            // Сохранение истории
            saveHistory(networkState)
            
            // Обновление виджетов
            WidgetUtils.updateAllWidgets(applicationContext, networkState)
            
            // Уведомления
            if (settings.enableNotifications) {
                processNotifications(resources, checkResults, previousResults, settings)
            }
            
            Result.success()
        } catch (e: Exception) {
            e.printStackTrace()
            Result.retry()
        }
    }
    
    private suspend fun saveHistory(networkState: NetworkState) {
        try {
            val entry = HistoryEntry(
                timestamp = System.currentTimeMillis(),
                availabilityIndex = networkState.availabilityIndex.value,
                networkMode = networkState.networkMode,
                availableCount = networkState.availableCount,
                unavailableCount = networkState.unavailableCount,
                details = ""
            )
            historyRepository.saveHistoryEntry(entry)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
    
    private suspend fun processNotifications(
        resources: List<Resource>,
        currentResults: List<CheckResult>,
        previousResults: Map<Long, CheckResult>,
        settings: com.netweather.domain.model.Settings
    ) {
        val currentMap = currentResults.associateBy { it.resourceId }
        
        resources.forEach { resource ->
            val current = currentMap[resource.id]
            val previous = previousResults[resource.id]
            
            if (current != null && previous != null) {
                val wasAvailable = previous.isSuccessful()
                val isAvailable = current.isSuccessful()
                
                if (settings.notifyOnFailure && wasAvailable && !isAvailable) {
                    notificationManager.notifyResourceFailure(
                        resource.name, current.getErrorDescription()
                    )
                }
                
                if (settings.notifyOnRecovery && !wasAvailable && isAvailable) {
                    notificationManager.notifyResourceRecovery(resource.name)
                }
                
                if (settings.notifyOnSlowResponse && isAvailable && 
                    current.responseTimeMs > settings.slowResponseThresholdMs) {
                    notificationManager.notifySlowResponse(
                        resource.name, current.responseTimeMs
                    )
                }
            }
        }
    }
    
    companion object {
        private const val WORK_NAME = "periodic_check_worker"
        
        fun enqueuePeriodicCheck(context: Context, intervalMinutes: Long = 15L) {
            val workRequest = PeriodicWorkRequestBuilder<PeriodicCheckWorker>(
                intervalMinutes, TimeUnit.MINUTES
            ).build()
            
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                workRequest
            )
        }
        
        fun cancelPeriodicCheck(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}