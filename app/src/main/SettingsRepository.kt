package com.netweather.domain.repository

import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import kotlinx.coroutines.flow.Flow

/**
 * Интерфейс репозитория для работы с настройками приложения
 */
interface SettingsRepository {
    
    fun getSettings(): Flow<Settings>
    
    suspend fun getSettingsOnce(): Settings
    
    suspend fun saveSettings(settings: Settings)
    
    suspend fun setThemeMode(themeMode: ThemeMode)
    
    suspend fun setCheckInterval(minutes: Int)
    
    suspend fun setConnectionTimeout(timeoutMs: Long)
    
    suspend fun setNotificationsEnabled(enabled: Boolean)
    
    suspend fun setNotifyOnFailure(enabled: Boolean)
    
    suspend fun setNotifyOnRecovery(enabled: Boolean)
    
    suspend fun setNotifyOnSlowResponse(enabled: Boolean)
    
    suspend fun setSlowResponseThreshold(thresholdMs: Long)
    
    suspend fun setHistoryRetentionDays(days: Int)
    
    suspend fun resetToDefaults()
}