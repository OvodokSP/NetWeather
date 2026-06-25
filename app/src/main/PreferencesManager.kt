package com.netweather.data.local.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PreferencesManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "netweather_preferences")

    companion object {
        private val KEY_THEME_MODE = stringPreferencesKey("theme_mode")
        private val KEY_CHECK_INTERVAL_MINUTES = intPreferencesKey("check_interval_minutes")
        private val KEY_CONNECTION_TIMEOUT_MS = longPreferencesKey("connection_timeout_ms")
        private val KEY_ENABLE_NOTIFICATIONS = booleanPreferencesKey("enable_notifications")
        private val KEY_NOTIFY_ON_FAILURE = booleanPreferencesKey("notify_on_failure")
        private val KEY_NOTIFY_ON_RECOVERY = booleanPreferencesKey("notify_on_recovery")
        private val KEY_NOTIFY_ON_SLOW_RESPONSE = booleanPreferencesKey("notify_on_slow_response")
        private val KEY_SLOW_RESPONSE_THRESHOLD_MS = longPreferencesKey("slow_response_threshold_ms")
        private val KEY_HISTORY_RETENTION_DAYS = intPreferencesKey("history_retention_days")
    }

    fun getSettings(): Flow<Settings> {
        return context.dataStore.data.map { preferences ->
            Settings(
                themeMode = try {
                    ThemeMode.valueOf(preferences[KEY_THEME_MODE] ?: ThemeMode.SYSTEM.name)
                } catch (e: IllegalArgumentException) {
                    ThemeMode.SYSTEM
                },
                checkIntervalMinutes = preferences[KEY_CHECK_INTERVAL_MINUTES] ?: Settings.DEFAULT_CHECK_INTERVAL_MINUTES,
                connectionTimeoutMs = preferences[KEY_CONNECTION_TIMEOUT_MS] ?: Settings.DEFAULT_CONNECTION_TIMEOUT_MS,
                enableNotifications = preferences[KEY_ENABLE_NOTIFICATIONS] ?: true,
                notifyOnFailure = preferences[KEY_NOTIFY_ON_FAILURE] ?: true,
                notifyOnRecovery = preferences[KEY_NOTIFY_ON_RECOVERY] ?: true,
                notifyOnSlowResponse = preferences[KEY_NOTIFY_ON_SLOW_RESPONSE] ?: false,
                slowResponseThresholdMs = preferences[KEY_SLOW_RESPONSE_THRESHOLD_MS] ?: Settings.DEFAULT_SLOW_RESPONSE_THRESHOLD_MS,
                historyRetentionDays = preferences[KEY_HISTORY_RETENTION_DAYS] ?: Settings.DEFAULT_HISTORY_RETENTION_DAYS
            )
        }
    }

    suspend fun saveSettings(settings: Settings) {
        context.dataStore.edit { preferences ->
            preferences[KEY_THEME_MODE] = settings.themeMode.name
            preferences[KEY_CHECK_INTERVAL_MINUTES] = settings.checkIntervalMinutes
            preferences[KEY_CONNECTION_TIMEOUT_MS] = settings.connectionTimeoutMs
            preferences[KEY_ENABLE_NOTIFICATIONS] = settings.enableNotifications
            preferences[KEY_NOTIFY_ON_FAILURE] = settings.notifyOnFailure
            preferences[KEY_NOTIFY_ON_RECOVERY] = settings.notifyOnRecovery
            preferences[KEY_NOTIFY_ON_SLOW_RESPONSE] = settings.notifyOnSlowResponse
            preferences[KEY_SLOW_RESPONSE_THRESHOLD_MS] = settings.slowResponseThresholdMs
            preferences[KEY_HISTORY_RETENTION_DAYS] = settings.historyRetentionDays
        }
    }

    suspend fun setThemeMode(themeMode: ThemeMode) {
        context.dataStore.edit { it[KEY_THEME_MODE] = themeMode.name }
    }

    suspend fun setCheckInterval(minutes: Int) {
        context.dataStore.edit { it[KEY_CHECK_INTERVAL_MINUTES] = minutes }
    }

    suspend fun setConnectionTimeout(timeoutMs: Long) {
        context.dataStore.edit { it[KEY_CONNECTION_TIMEOUT_MS] = timeoutMs }
    }

    suspend fun setNotificationsEnabled(enabled: Boolean) {
        context.dataStore.edit { it[KEY_ENABLE_NOTIFICATIONS] = enabled }
    }

    suspend fun setNotifyOnFailure(enabled: Boolean) {
        context.dataStore.edit { it[KEY_NOTIFY_ON_FAILURE] = enabled }
    }

    suspend fun setNotifyOnRecovery(enabled: Boolean) {
        context.dataStore.edit { it[KEY_NOTIFY_ON_RECOVERY] = enabled }
    }

    suspend fun setNotifyOnSlowResponse(enabled: Boolean) {
        context.dataStore.edit { it[KEY_NOTIFY_ON_SLOW_RESPONSE] = enabled }
    }

    suspend fun setSlowResponseThreshold(thresholdMs: Long) {
        context.dataStore.edit { it[KEY_SLOW_RESPONSE_THRESHOLD_MS] = thresholdMs }
    }

    suspend fun setHistoryRetentionDays(days: Int) {
        context.dataStore.edit { it[KEY_HISTORY_RETENTION_DAYS] = days }
    }

    suspend fun resetToDefaults() {
        context.dataStore.edit { it.clear() }
    }
}