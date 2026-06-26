package com.netweather.data.repository

import com.netweather.data.local.preferences.PreferencesManager
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import com.netweather.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepositoryImpl @Inject constructor(
    private val preferencesManager: PreferencesManager
) : SettingsRepository {

    override fun getSettings(): Flow<Settings> = preferencesManager.getSettings()
    override suspend fun getSettingsOnce(): Settings {
        var settings = Settings()
        preferencesManager.getSettings().collect { settings = it }
        return settings
    }
    override suspend fun saveSettings(settings: Settings) = preferencesManager.saveSettings(settings)
    override suspend fun setThemeMode(themeMode: ThemeMode) = preferencesManager.setThemeMode(themeMode)
    override suspend fun setCheckInterval(minutes: Int) = preferencesManager.setCheckInterval(minutes)
    override suspend fun setConnectionTimeout(timeoutMs: Long) = preferencesManager.setConnectionTimeout(timeoutMs)
    override suspend fun setNotificationsEnabled(enabled: Boolean) = preferencesManager.setNotificationsEnabled(enabled)
    override suspend fun setNotifyOnFailure(enabled: Boolean) = preferencesManager.setNotifyOnFailure(enabled)
    override suspend fun setNotifyOnRecovery(enabled: Boolean) = preferencesManager.setNotifyOnRecovery(enabled)
    override suspend fun setNotifyOnSlowResponse(enabled: Boolean) = preferencesManager.setNotifyOnSlowResponse(enabled)
    override suspend fun setSlowResponseThreshold(thresholdMs: Long) = preferencesManager.setSlowResponseThreshold(thresholdMs)
    override suspend fun setHistoryRetentionDays(days: Int) = preferencesManager.setHistoryRetentionDays(days)
    override suspend fun resetToDefaults() = preferencesManager.resetToDefaults()
}