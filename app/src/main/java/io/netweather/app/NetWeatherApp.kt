package io.netweather.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import io.netweather.app.worker.MonitoringScheduler

@HiltAndroidApp
class NetWeatherApp : Application() {
    override fun onCreate() {
        super.onCreate()
        MonitoringScheduler.ensureScheduled(this)
    }
}
