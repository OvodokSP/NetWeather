package com.netweather.worker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.netweather.domain.repository.SettingsRepository
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

/**
 * Перезапускает фоновые задачи после перезагрузки устройства
 */
@AndroidEntryPoint
class BootReceiver : BroadcastReceiver() {
    
    @Inject
    lateinit var settingsRepository: SettingsRepository
    
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || 
            intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            WorkerScheduler.initialize(context, settingsRepository)
        }
    }
}