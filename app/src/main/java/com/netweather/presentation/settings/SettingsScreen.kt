package com.netweather.presentation.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.netweather.presentation.settings.components.IntervalSelector
import com.netweather.presentation.settings.components.NotificationsSettings
import com.netweather.presentation.settings.components.ResourceGroupManager
import com.netweather.presentation.settings.components.SettingsCard
import com.netweather.presentation.settings.components.ThemeSelector

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    
    LaunchedEffect(uiState.error) {
        uiState.error?.let { error ->
            snackbarHostState.showSnackbar(
                message = error,
                actionLabel = "OK"
            )
            viewModel.clearError()
        }
    }
    
    LaunchedEffect(uiState.successMessage) {
        uiState.successMessage?.let { message ->
            snackbarHostState.showSnackbar(
                message = message,
                actionLabel = "OK"
            )
            viewModel.clearSuccessMessage()
        }
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Настройки",
                        style = MaterialTheme.typography.headlineMedium
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Внешний вид
            item {
                Text(
                    text = "Внешний вид",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            
            item {
                ThemeSelector(
                    currentTheme = uiState.settings.themeMode,
                    onThemeSelected = { themeMode ->
                        viewModel.setThemeMode(themeMode)
                    }
                )
            }
            
            // Интервал проверки
            item {
                Text(
                    text = "Интервал проверки",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            
            item {
                IntervalSelector(
                    currentInterval = uiState.settings.checkIntervalMinutes,
                    onIntervalSelected = { minutes ->
                        viewModel.setCheckInterval(minutes)
                    }
                )
            }
            
            // Уведомления
            item {
                Text(
                    text = "Уведомления",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            
            item {
                NotificationsSettings(
                    settings = uiState.settings,
                    onNotificationsEnabledChanged = { enabled ->
                        viewModel.setNotificationsEnabled(enabled)
                    },
                    onNotifyOnFailureChanged = { enabled ->
                        viewModel.setNotifyOnFailure(enabled)
                    },
                    onNotifyOnRecoveryChanged = { enabled ->
                        viewModel.setNotifyOnRecovery(enabled)
                    },
                    onNotifyOnSlowResponseChanged = { enabled ->
                        viewModel.setNotifyOnSlowResponse(enabled)
                    }
                )
            }
            
            // Управление ресурсами
            item {
                Text(
                    text = "Управление ресурсами",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            
            item {
                ResourceGroupManager(
                    russianResources = uiState.russianResources,
                    internationalResources = uiState.internationalResources,
                    customResources = uiState.customResources,
                    onToggleResource = { resourceId ->
                        viewModel.toggleResource(resourceId)
                    },
                    onDeleteResource = { resourceId ->
                        viewModel.deleteResource(resourceId)
                    },
                    onAddResource = { name, url ->
                        viewModel.addCustomResource(name, url)
                    }
                )
            }
            
            // История
            item {
                Text(
                    text = "История",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
            
            item {
                HistorySettings(
                    retentionDays = uiState.settings.historyRetentionDays,
                    onRetentionDaysChanged = { days ->
                        viewModel.setHistoryRetentionDays(days)
                    }
                )
            }
            
            // Сброс настроек
            item {
                Spacer(modifier = Modifier.height(16.dp))
                
                ResetSettingsButton(
                    onReset = {
                        viewModel.resetSettings()
                    }
                )
            }
            
            // Отступ внизу
            item {
                Spacer(modifier = Modifier.height(32.dp))
            }
        }
    }
}

@Composable
private fun HistorySettings(
    retentionDays: Int,
    onRetentionDaysChanged: (Int) -> Unit
) {
    SettingsCard(title = "Хранение истории") {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Хранить историю: $retentionDays дней",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            Slider(
                value = retentionDays.toFloat(),
                onValueChange = { value ->
                    onRetentionDaysChanged(value.toInt())
                },
                valueRange = 1f..30f,
                steps = 28
            )
            
            Text(
                text = "От 1 до 30 дней",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ResetSettingsButton(
    onReset: () -> Unit
) {
    OutlinedButton(
        onClick = onReset,
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(text = "Сбросить настройки по умолчанию")
    }
}