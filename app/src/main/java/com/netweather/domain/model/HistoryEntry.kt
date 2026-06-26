package com.netweather.domain.model

/**
 * Запись истории состояния сети
 */
data class HistoryEntry(
    val id: Long = 0,
    val timestamp: Long = System.currentTimeMillis(),
    val availabilityIndex: Int,
    val networkMode: NetworkMode,
    val availableCount: Int,
    val unavailableCount: Int,
    val details: String = ""
) {
    fun getTotalCount(): Int = availableCount + unavailableCount
    
    fun getAvailabilityPercentage(): Int {
        val total = getTotalCount()
        return if (total > 0) {
            (availableCount * 100) / total
        } else {
            0
        }
    }
    
    fun getUnavailabilityPercentage(): Int {
        val total = getTotalCount()
        return if (total > 0) {
            (unavailableCount * 100) / total
        } else {
            0
        }
    }
}

/**
 * Период истории для фильтрации
 */
enum class HistoryPeriod {
    HOUR,
    DAY,
    WEEK;
    
    fun getDurationMs(): Long {
        return when (this) {
            HOUR -> 60 * 60 * 1000L
            DAY -> 24 * 60 * 60 * 1000L
            WEEK -> 7 * 24 * 60 * 60 * 1000L
        }
    }
    
    fun getTitle(): String {
        return when (this) {
            HOUR -> "1 час"
            DAY -> "24 часа"
            WEEK -> "7 дней"
        }
    }
}