package io.netweather.app.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import io.netweather.app.R
import io.netweather.app.domain.model.*

class AppNotifier(private val context: Context) {
    private val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    init { if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel(CHANNEL, "NetWeather", NotificationManager.IMPORTANCE_DEFAULT)) }
    fun notifyChanges(resources: List<MonitoredResource>, previous: Map<Long, CheckResult>, current: List<CheckResult>) {
        val currentMap = current.associateBy { it.resourceId }
        resources.forEach { r ->
            val before = previous[r.id]
            val now = currentMap[r.id] ?: return@forEach
            if (before?.isOk == true && !now.isOk) notify("${r.name} недоступен", now.status.title)
            if (before != null && !before.isOk && now.isOk) notify("${r.name} восстановлен", "Ресурс снова доступен")
            if (now.isOk && now.responseTimeMs > 1500) notify("${r.name}: медленный отклик", "${now.responseTimeMs} мс")
        }
    }
    private fun notify(title: String, text: String) { manager.notify((System.currentTimeMillis()%Int.MAX_VALUE).toInt(), NotificationCompat.Builder(context, CHANNEL).setSmallIcon(R.drawable.ic_launcher_foreground).setContentTitle(title).setContentText(text).setAutoCancel(true).build()) }
    companion object { private const val CHANNEL = "netweather_alerts" }
}
