package io.netweather.app.worker

import android.content.Context
import androidx.work.*
import java.util.concurrent.TimeUnit

object MonitoringScheduler {
    private const val UNIQUE = "netweather_monitoring_work"
    fun ensureScheduled(context: Context) = reschedule(context, 300)
    fun reschedule(context: Context, intervalSeconds: Int) {
        WorkManager.getInstance(context).cancelUniqueWork(UNIQUE)
        if (intervalSeconds < 900) scheduleOneTime(context, intervalSeconds) else schedulePeriodic(context, intervalSeconds)
    }
    fun scheduleOneTime(context: Context, intervalSeconds: Int) {
        val request = OneTimeWorkRequestBuilder<MonitoringWorker>().setInitialDelay(intervalSeconds.toLong(), TimeUnit.SECONDS).setInputData(workDataOf("intervalSeconds" to intervalSeconds)).build()
        WorkManager.getInstance(context).enqueueUniqueWork(UNIQUE, ExistingWorkPolicy.REPLACE, request)
    }
    private fun schedulePeriodic(context: Context, intervalSeconds: Int) {
        val request = PeriodicWorkRequestBuilder<MonitoringWorker>(intervalSeconds.toLong(), TimeUnit.SECONDS).setInputData(workDataOf("intervalSeconds" to intervalSeconds)).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(UNIQUE, ExistingPeriodicWorkPolicy.UPDATE, request)
    }
}
