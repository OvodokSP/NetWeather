package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.Settings

@Composable
fun NotificationsSettings(
    settings: Settings,
    onNotificationsEnabledChanged: (Boolean) -> Unit,
    onNotifyOnFailureChanged: (Boolean) -> Unit,
    onNotifyOnRecoveryChanged: (Boolean) -> Unit,
    onNotifyOnSlowResponseChanged: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    SettingsCard(
        title = "Уведомления",
        modifier = modifier
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            NotificationToggle(
                title = "Включить уведомления",
                description = "Получать уведомления о состоянии сети",
                isChecked = settings.enableNotifications,
                onCheckedChange = onNotificationsEnabledChanged
            )
            
            if (settings.enableNotifications) {
                NotificationToggle(
                    title = "Уведомлять о сбоях",
                    description = "Когда ресурс становится недоступен",
                    isChecked = settings.notifyOnFailure,
                    onCheckedChange = onNotifyOnFailureChanged
                )
                
                NotificationToggle(
                    title = "Уведомлять о восстановлении",
                    description = "Когда ресурс снова становится доступен",
                    isChecked = settings.notifyOnRecovery,
                    onCheckedChange = onNotifyOnRecoveryChanged
                )
                
                NotificationToggle(
                    title = "Уведомлять о медленном отклике",
                    description = "Когда время отклика превышает порог",
                    isChecked = settings.notifyOnSlowResponse,
                    onCheckedChange = onNotifyOnSlowResponseChanged
                )
            }
        }
    }
}

@Composable
private fun NotificationToggle(
    title: String,
    description: String,
    isChecked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        
        Switch(
            checked = isChecked,
            onCheckedChange = onCheckedChange
        )
    }
}