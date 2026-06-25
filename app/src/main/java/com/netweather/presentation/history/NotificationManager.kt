package com.netweather.notification

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager as AndroidNotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.netweather.MainActivity
import com.netweather.R
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.NetworkState
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NotificationManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    
    private val notificationManager = NotificationManagerCompat.from(context)
    
    companion object {
        const val CHANNEL_ID_FAILURE = "resource_failure"
        const val CHANNEL_ID_RECOVERY = "resource_recovery"
        const val CHANNEL_ID_SLOW_RESPONSE = "slow_response"
        const val CHANNEL_ID_NETWORK_MODE = "network_mode_change"
        
        private const val NOTIFICATION_ID_BASE = 1000
        private var notificationIdCounter = NOTIFICATION_ID_BASE
    }
    
    init {
        createNotificationChannels()
    }
    
    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as AndroidNotificationManager
            
            val channels = listOf(
                NotificationChannel(CHANNEL_ID_FAILURE, "Сбои ресурсов", AndroidNotificationManager.IMPORTANCE_HIGH),
                NotificationChannel(CHANNEL_ID_RECOVERY, "Восстановление ресурсов", AndroidNotificationManager.IMPORTANCE_DEFAULT),
                NotificationChannel(CHANNEL_ID_SLOW_RESPONSE, "Медленный отклик", AndroidNotificationManager.IMPORTANCE_LOW),
                NotificationChannel(CHANNEL_ID_NETWORK_MODE, "Изменение режима сети", AndroidNotificationManager.IMPORTANCE_DEFAULT)
            )
            
            channels[0].description = "Уведомления когда ресурс становится недоступен"
            channels[1].description = "Уведомления когда ресурс снова становится доступен"
            channels[2].description = "Уведомления когда время отклика превышает порог"
            channels[3].description = "Уведомления об изменении режима сети"
            
            manager.createNotificationChannels(channels)
        }
    }
    
    private fun createPendingIntent(): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        return PendingIntent.getActivity(
            context, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }
    
    private fun hasPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
    }
    
    fun notifyResourceFailure(resourceName: String, errorDescription: String) {
        if (!hasPermission()) return
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_FAILURE)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Ресурс недоступен")
            .setContentText("$resourceName: $errorDescription")
            .setStyle(NotificationCompat.BigTextStyle().bigText("$resourceName недоступен.\n$errorDescription"))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(createPendingIntent())
            .setAutoCancel(true)
            .build()
        
        try {
            notificationManager.notify(getUniqueNotificationId(), notification)
        } catch (e: SecurityException) {
            e.printStackTrace()
        }
    }
    
    fun notifyResourceRecovery(resourceName: String) {
        if (!hasPermission()) return
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_RECOVERY)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Ресурс восстановлен")
            .setContentText("$resourceName снова доступен")
            .setStyle(NotificationCompat.BigTextStyle().bigText("$resourceName снова доступен и работает нормально."))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(createPendingIntent())
            .setAutoCancel(true)
            .build()
        
        try {
            notificationManager.notify(getUniqueNotificationId(), notification)
        } catch (e: SecurityException) {
            e.printStackTrace()
        }
    }
    
    fun notifySlowResponse(resourceName: String, responseTimeMs: Long) {
        if (!hasPermission()) return
        
        val seconds = responseTimeMs / 1000.0
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_SLOW_RESPONSE)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Медленный отклик")
            .setContentText("$resourceName: ${String.format("%.1f", seconds)} сек")
            .setStyle(NotificationCompat.BigTextStyle().bigText("$resourceName отвечает медленно.\nВремя отклика: ${String.format("%.1f", seconds)} секунд"))
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(createPendingIntent())
            .setAutoCancel(true)
            .build()
        
        try {
            notificationManager.notify(getUniqueNotificationId(), notification)
        } catch (e: SecurityException) {
            e.printStackTrace()
        }
    }
    
    fun notifyNetworkModeChange(networkState: NetworkState) {
        if (!hasPermission()) return
        
        val title = when (networkState.networkMode) {
            NetworkMode.NORMAL -> "Сеть восстановлена"
            NetworkMode.PARTIAL_DEGRADATION -> "Частичная деградация сети"
            NetworkMode.RESTRICTED_ACCESS -> "Ограничения доступа"
            NetworkMode.NO_INTERNET -> "Нет доступа в интернет"
        }
        
        val text = "${networkState.networkMode.getEmoji()} ${networkState.networkMode.getTitle()}\nДоступно: ${networkState.availableCount}/${networkState.totalResources}"
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_NETWORK_MODE)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(createPendingIntent())
            .setAutoCancel(true)
            .build()
        
        try {
            notificationManager.notify(getUniqueNotificationId(), notification)
        } catch (e: SecurityException) {
            e.printStackTrace()
        }
    }
    
    private fun getUniqueNotificationId(): Int = notificationIdCounter++
}