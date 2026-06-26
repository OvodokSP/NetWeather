package com.netweather.domain.model

/**
 * Режим сети на основе результатов проверки
 */
enum class NetworkMode {
    NORMAL,
    PARTIAL_DEGRADATION,
    RESTRICTED_ACCESS,
    NO_INTERNET;
    
    fun getEmoji(): String {
        return when (this) {
            NORMAL -> "🟢"
            PARTIAL_DEGRADATION -> "🟡"
            RESTRICTED_ACCESS -> "🟠"
            NO_INTERNET -> "🔴"
        }
    }
    
    fun getTitle(): String {
        return when (this) {
            NORMAL -> "Нормальный доступ"
            PARTIAL_DEGRADATION -> "Частичная деградация"
            RESTRICTED_ACCESS -> "Вероятны ограничения доступа"
            NO_INTERNET -> "Нет доступа в интернет"
        }
    }
    
    fun getDescription(): String {
        return when (this) {
            NORMAL -> "Большинство ресурсов доступны. Сеть работает стабильно."
            PARTIAL_DEGRADATION -> "Недоступно менее 30% ресурсов. Возможны временные проблемы."
            RESTRICTED_ACCESS -> "Вероятны ограничения доступа к части зарубежных ресурсов."
            NO_INTERNET -> "Недоступны большинство ресурсов. Проверьте подключение к интернету."
        }
    }
    
    fun getShortDescription(): String {
        return when (this) {
            NORMAL -> "Всё работает"
            PARTIAL_DEGRADATION -> "Частичные проблемы"
            RESTRICTED_ACCESS -> "Ограничения доступа"
            NO_INTERNET -> "Нет интернета"
        }
    }
}