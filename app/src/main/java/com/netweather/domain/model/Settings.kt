package com.netweather.domain.model

/**
 * Настройки приложения
 */
data class Settings(
    val themeMode: ThemeMode = ThemeMode.SYSTEM,
    val checkIntervalMinutes: Int = DEFAULT_CHECK_INTERVAL_MINUTES,
    val connectionTimeoutMs: Long = DEFAULT_CONNECTION_TIMEOUT_MS,
    val enableNotifications: Boolean = true,
    val notifyOnFailure: Boolean = true,
    val notifyOnRecovery: Boolean = true,
    val notifyOnSlowResponse: Boolean = false,
    val slowResponseThresholdMs: Long = DEFAULT_SLOW_RESPONSE_THRESHOLD_MS,
    val historyRetentionDays: Int = DEFAULT_HISTORY_RETENTION_DAYS,
    val enableWidgetsEnabled: Boolean = true
) {
    companion object {
        const val DEFAULT_CHECK_INTERVAL_MINUTES = 15
        const val MIN_CHECK_INTERVAL_MINUTES = 0
        const val MAX_CHECK_INTERVAL_MINUTES = 60
        
        const val DEFAULT_CONNECTION_TIMEOUT_MS = 10000L
        const val MIN_CONNECTION_TIMEOUT_MS = 3000L
        const val MAX_CONNECTION_TIMEOUT_MS = 30000L
        
        const val DEFAULT_SLOW_RESPONSE_THRESHOLD_MS = 5000L
        const val MIN_SLOW_RESPONSE_THRESHOLD_MS = 1000L
        const val MAX_SLOW_RESPONSE_THRESHOLD_MS = 30000L
        
        const val DEFAULT_HISTORY_RETENTION_DAYS = 7
        const val MIN_HISTORY_RETENTION_DAYS = 1
        const val MAX_HISTORY_RETENTION_DAYS = 30
    }
    
    fun getCheckIntervalMs(): Long {
        return if (checkIntervalMinutes == 0) 30_000L else checkIntervalMinutes * 60 * 1000L
    }
    
    fun isValid(): Boolean {
        return checkIntervalMinutes in MIN_CHECK_INTERVAL_MINUTES..MAX_CHECK_INTERVAL_MINUTES &&
               connectionTimeoutMs in MIN_CONNECTION_TIMEOUT_MS..MAX_CONNECTION_TIMEOUT_MS &&
               slowResponseThresholdMs in MIN_SLOW_RESPONSE_THRESHOLD_MS..MAX_SLOW_RESPONSE_THRESHOLD_MS &&
               historyRetentionDays in MIN_HISTORY_RETENTION_DAYS..MAX_HISTORY_RETENTION_DAYS
    }
}

/**
 * Режим темы приложения
 */
enum class ThemeMode {
    LIGHT,
    DARK,
    SYSTEM;
    
    fun getTitle(): String {
        return when (this) {
            LIGHT -> "Светлая"
            DARK -> "Тёмная"
            SYSTEM -> "Системная"
        }
    }
}