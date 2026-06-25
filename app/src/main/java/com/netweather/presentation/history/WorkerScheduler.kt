package com.netweather.worker

import android.content.Context
import com.netweather.domain.repository.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

/**
 * Планировщик фоновых задач
 */
object WorkerScheduler {
    
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    /**
     * Инициализация всех планировщиков
     */
    fun initialize(context: Context, settingsRepository: SettingsRepository) {
        scope.launch {
            try {
                val settings = settingsRepository.getSettingsOnce()
                
                PeriodicCheckWorker.enqueuePeriodicCheck(
                    context,
                    settings.checkIntervalMinutes.toLong()
                )
                
                CleanupWorker.enqueuePeriodicCleanup(context)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
    
    /**
     * Обновление интервала проверки (при изменении настроек)
     */
    fun updateCheckInterval(context: Context, intervalMinutes: Int) {
        PeriodicCheckWorker.cancelPeriodicCheck(context)
        PeriodicCheckWorker.enqueuePeriodicCheck(context, intervalMinutes.toLong())
    }
}