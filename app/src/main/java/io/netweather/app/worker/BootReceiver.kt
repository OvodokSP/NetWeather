package io.netweather.app.worker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import io.netweather.app.data.StateStore

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            MonitoringScheduler.ensureScheduled(
                context,
                StateStore(context).loadIntervalSeconds(),
            )
        }
    }
}
