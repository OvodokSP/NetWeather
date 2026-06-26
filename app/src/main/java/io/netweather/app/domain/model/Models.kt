package io.netweather.app.domain.model

import kotlinx.serialization.Serializable

enum class ResourceGroup(val title: String) { RUSSIAN("Российские"), INTERNATIONAL("Международные"), CUSTOM("Пользовательские") }
enum class CheckMethod(val title: String) { DNS("DNS"), TCP("TCP"), HTTPS_GET("HTTPS GET"), HTTPS_HEAD("HTTPS HEAD"), HTTP_GET("HTTP GET"), HTTP_HEAD("HTTP HEAD"), CUSTOM_URL("Custom URL") }
enum class DiagnosticStatus(val title: String) {
    OK("Работает"), DNS_ERROR("Ошибка DNS"), TCP_ERROR("Ошибка TCP"), TLS_ERROR("Ошибка TLS"), HTTP_ERROR("Ошибка HTTP"), TIMEOUT("Таймаут"), CONTENT_ERROR("Ошибка содержимого"), UNKNOWN_ERROR("Неизвестная ошибка")
}
enum class NetworkMode(val title: String, val emoji: String) { NORMAL("Нормальный доступ","🟢"), PARTIAL_DEGRADATION("Частичная деградация","🟡"), RESTRICTED_ACCESS("Вероятны ограничения доступа","🟠"), NO_INTERNET("Нет доступа в интернет","🔴") }

@Serializable
data class MonitoredResource(
    val id: Long = 0,
    val name: String,
    val url: String,
    val group: ResourceGroup,
    val method: CheckMethod = CheckMethod.HTTPS_GET,
    val intervalSeconds: Int = 300,
    val priority: Int = 0,
    val enabled: Boolean = true
)

data class CheckResult(
    val resourceId: Long,
    val status: DiagnosticStatus,
    val responseTimeMs: Long,
    val timestamp: Long = System.currentTimeMillis(),
    val lastSuccessfulCheck: Long? = null,
    val message: String = ""
) { val isOk: Boolean get() = status == DiagnosticStatus.OK }

data class NetworkSummary(
    val availabilityIndex: Int = 0,
    val mode: NetworkMode = NetworkMode.NO_INTERNET,
    val lastUpdated: Long = 0,
    val total: Int = 0,
    val available: Int = 0,
    val problematic: Int = 0,
    val problemNames: List<String> = emptyList()
)

data class ResourceWithResult(val resource: MonitoredResource, val result: CheckResult?)

data class Settings(
    val darkTheme: Boolean = false,
    val checkIntervalSeconds: Int = 300,
    val notificationsEnabled: Boolean = true,
    val slowResponseThresholdMs: Long = 1500
)
