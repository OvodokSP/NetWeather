package com.netweather.domain.model

/**
 * Модель ресурса для мониторинга
 */
data class Resource(
    val id: Long = 0,
    val name: String,
    val url: String,
    val group: ResourceGroup,
    val enabled: Boolean = true,
    val createdAt: Long = System.currentTimeMillis()
) {
    fun isValidUrl(): Boolean {
        return url.isNotBlank() && 
               (url.startsWith("http://") || url.startsWith("https://"))
    }
    
    fun extractDomain(): String {
        return try {
            val withoutProtocol = url.removePrefix("http://").removePrefix("https://")
            withoutProtocol.split("/").firstOrNull()?.split(":")?.first() ?: ""
        } catch (e: Exception) {
            ""
        }
    }
}

/**
 * Группа ресурсов
 */
enum class ResourceGroup {
    RU,
    INTL,
    CUSTOM
}