package io.netweather.app.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.room.Room
import io.netweather.app.data.*
import io.netweather.app.data.local.AppDatabase
import io.netweather.app.data.network.NetworkDiagnostics
import io.netweather.app.data.network.NetWeatherApi
import io.netweather.app.domain.logic.NetworkAnalyzer
import io.netweather.app.notification.AppNotifier
import io.netweather.app.domain.repository.NetWeatherRepository

class MonitoringWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        val repo: NetWeatherRepository = createRepo(applicationContext)
        repo.runChecks()
        val interval = inputData.getInt("intervalSeconds", 300)
        if (interval < 900) MonitoringScheduler.scheduleOneTime(applicationContext, interval)
        Result.success()
    } catch (e: Exception) { Result.retry() }
    companion object { fun createRepo(context: Context): NetWeatherRepository { val db = Room.databaseBuilder(context, AppDatabase::class.java, "netweather.db").build(); val state = StateStore(context); return NetWeatherRepositoryImpl(context, db, NetworkDiagnostics(), NetWeatherApi(stateStore = state), NetworkAnalyzer(), state, AppNotifier(context)) } }
}
