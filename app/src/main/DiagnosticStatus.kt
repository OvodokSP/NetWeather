package com.netweather.domain.model

/**
 * Статус диагностики для каждого этапа проверки
 */
enum class DiagnosticStatus {
    OK,
    DNS_ERROR,
    TCP_ERROR,
    TLS_ERROR,
    HTTP_ERROR,
    TIMEOUT,
    CONTENT_ERROR,
    UNKNOWN_ERROR;
    
    fun isSuccessful(): Boolean = this == OK
    
    fun isError(): Boolean = this != OK
    
    fun getDescription(): String {
        return when (this) {
            OK -> "Успешно"
            DNS_ERROR -> "Ошибка DNS"
            TCP_ERROR -> "Ошибка TCP"
            TLS_ERROR -> "Ошибка TLS"
            HTTP_ERROR -> "Ошибка HTTP"
            TIMEOUT -> "Таймаут"
            CONTENT_ERROR -> "Ошибка содержимого"
            UNKNOWN_ERROR -> "Неизвестная ошибка"
        }
    }
    
    fun getDetailedDescription(): String {
        return when (this) {
            OK -> "Проверка пройдена успешно"
            DNS_ERROR -> "Не удалось разрешить доменное имя. Проверьте настройки DNS или подключение к интернету."
            TCP_ERROR -> "Не удалось установить соединение с сервером. Сервер может быть недоступен или заблокирован."
            TLS_ERROR -> "Ошибка установки защищённого соединения. Проблемы с SSL/TLS сертификатом."
            HTTP_ERROR -> "Сервер вернул ошибку. Ресурс может быть временно недоступен."
            TIMEOUT -> "Превышено время ожидания ответа. Сервер не отвечает или соединение слишком медленное."
            CONTENT_ERROR -> "Содержимое ответа не соответствует ожидаемому. Возможна блокировка или редирект."
            UNKNOWN_ERROR -> "Произошла неизвестная ошибка при проверке ресурса."
        }
    }
}