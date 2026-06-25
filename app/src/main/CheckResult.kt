package com.netweather.domain.model

/**
 * Результат проверки ресурса
 */
data class CheckResult(
    val id: Long = 0,
    val resourceId: Long,
    val timestamp: Long = System.currentTimeMillis(),
    val dnsStatus: DiagnosticStatus,
    val tcpStatus: DiagnosticStatus,
    val tlsStatus: DiagnosticStatus,
    val httpStatus: DiagnosticStatus,
    val contentStatus: DiagnosticStatus,
    val responseTimeMs: Long,
    val errorMessage: String? = null
) {
    fun isSuccessful(): Boolean {
        return dnsStatus == DiagnosticStatus.OK &&
               tcpStatus == DiagnosticStatus.OK &&
               tlsStatus == DiagnosticStatus.OK &&
               httpStatus == DiagnosticStatus.OK &&
               contentStatus == DiagnosticStatus.OK
    }
    
    fun getFirstErrorStatus(): DiagnosticStatus {
        return when {
            dnsStatus != DiagnosticStatus.OK -> dnsStatus
            tcpStatus != DiagnosticStatus.OK -> tcpStatus
            tlsStatus != DiagnosticStatus.OK -> tlsStatus
            httpStatus != DiagnosticStatus.OK -> httpStatus
            contentStatus != DiagnosticStatus.OK -> contentStatus
            else -> DiagnosticStatus.OK
        }
    }
    
    fun getErrorDescription(): String {
        return when (getFirstErrorStatus()) {
            DiagnosticStatus.OK -> "Все проверки пройдены успешно"
            DiagnosticStatus.DNS_ERROR -> "Не удалось разрешить DNS"
            DiagnosticStatus.TCP_ERROR -> "Не удалось установить TCP соединение"
            DiagnosticStatus.TLS_ERROR -> "Ошибка TLS рукопожатия"
            DiagnosticStatus.HTTP_ERROR -> "Ошибка HTTP запроса"
            DiagnosticStatus.TIMEOUT -> "Превышено время ожидания"
            DiagnosticStatus.CONTENT_ERROR -> "Содержимое не соответствует ожидаемому"
            DiagnosticStatus.UNKNOWN_ERROR -> errorMessage ?: "Неизвестная ошибка"
        }
    }
}