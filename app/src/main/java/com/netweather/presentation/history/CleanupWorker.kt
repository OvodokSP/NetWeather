package com.netweather.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.HistoryRepository
import com.netweather.domain.repository.SettingsRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

/**
 * Worker для очистки старых данных из базы
 * Запускается раз в сутки
 */
@HiltWorker
class CleanupWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val historyRepository: HistoryRepository,
    private val settingsRepository: SettingsRepository
) : CoroutineWorker(context, workerParams) {
    
    override suspend fun doWork(): Result {
        return try {
            val settings = settingsRepository.getSettingsOnce()
            val retentionMs = settings.historyRetentionDays * 24L * 60L * 60L * 1000L
            
            diagnosticsRepository.deleteOldCheckResults(retentionMs)
            historyRepository.deleteOldHistory(retentionMs)
            
            Result.success()
        } catch (e: Exception) {
            e.printStackTrace()
            Result.retry()
        }
    }
    
    companion object {
        private const val WORK_NAME = "cleanup_worker"
        
        fun enqueuePeriodicCleanup(context: Context) {
            val workRequest = PeriodicWorkRequestBuilder<CleanupWorker>(
                1, TimeUnit.DAYS
            ).build()
            
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                workRequest
            )
        }
    }
}