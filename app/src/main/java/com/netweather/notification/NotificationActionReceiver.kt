package com.netweather.notification

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.netweather.worker.WorkerScheduler
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

/**
 * Обработчик действий из уведомлений
 */
@AndroidEntryPoint
class NotificationActionReceiver : BroadcastReceiver() {
    
    @Inject
    lateinit var notificationManager: NotificationManager
    
    companion object {
        const val ACTION_DISMISS = "com.netweather.action.DISMISS_NOTIFICATION"
        const val ACTION_REFRESH = "com.netweather.action.REFRESH_NOW"
    }
    
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_REFRESH -> {
                WorkerScheduler.initialize(context, (context.applicationContext as com.netweather.NetWeatherApp).settingsRepository)
            }
        }
    }
}