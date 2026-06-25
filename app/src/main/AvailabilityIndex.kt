package com.netweather.domain.model

/**
 * Индекс доступности сети (0-100%)
 */
data class AvailabilityIndex(
    val value: Int,
    val internetWeight: Int = DEFAULT_INTERNET_WEIGHT,
    val ruWeight: Int = DEFAULT_RU_WEIGHT,
    val intlWeight: Int = DEFAULT_INTL_WEIGHT,
    val customWeight: Int = DEFAULT_CUSTOM_WEIGHT
) {
    companion object {
        const val DEFAULT_INTERNET_WEIGHT = 40
        const val DEFAULT_RU_WEIGHT = 20
        const val DEFAULT_INTL_WEIGHT = 20
        const val DEFAULT_CUSTOM_WEIGHT = 20
        
        const val MIN_VALUE = 0
        const val MAX_VALUE = 100
        
        /**
         * Создание индекса с валидацией значения
         */
        fun create(value: Int): AvailabilityIndex {
            val clampedValue = value.coerceIn(MIN_VALUE, MAX_VALUE)
            return AvailabilityIndex(clampedValue)
        }
    }
    
    init {
        require(value in MIN_VALUE..MAX_VALUE) {
            "Значение индекса должно быть в диапазоне от $MIN_VALUE до $MAX_VALUE"
        }
        require(internetWeight + ruWeight + intlWeight + customWeight == 100) {
            "Сумма весовых коэффициентов должна равняться 100"
        }
    }
    
    fun isGood(): Boolean = value >= 80
    
    fun isAcceptable(): Boolean = value >= 70
    
    fun isBad(): Boolean = value < 30
    
    fun getPercentage(): Int = value
    
    fun toPercentageString(): String = "$value%"
    
    fun getColorIndicator(): String {
        return when {
            value >= 80 -> "GREEN"
            value >= 70 -> "YELLOW"
            value >= 30 -> "ORANGE"
            else -> "RED"
        }
    }
}