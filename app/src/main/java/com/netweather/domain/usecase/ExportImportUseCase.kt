package com.netweather.domain.usecase

import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject

/**
 * Use case для экспорта и импорта данных приложения
 */
class ExportImportUseCase @Inject constructor(
    private val resourceRepository: ResourceRepository,
    private val settingsRepository: SettingsRepository
) {
    
    private val json = Json { 
        prettyPrint = true
        ignoreUnknownKeys = true
    }
    
    /**
     * Экспорт всех данных в JSON
     */
    suspend fun exportData(): Result<String> {
        return try {
            val resources = resourceRepository.getAllResourcesOnce()
            val settings = settingsRepository.getSettingsOnce()
            
            val exportData = ExportData(
                version = 1,
                timestamp = System.currentTimeMillis(),
                resources = resources.map { it.toExportResource() },
                settings = settings.toExportSettings()
            )
            
            val jsonString = json.encodeToString(exportData)
            Result.success(jsonString)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Импорт данных из JSON
     */
    suspend fun importData(jsonString: String): Result<ImportResult> {
        return try {
            val importData = json.decodeFromString<ExportData>(jsonString)
            
            if (importData.version > 1) {
                return Result.failure(UnsupportedOperationException("Неподдерживаемая версия данных"))
            }
            
            var importedResources = 0
            var skippedResources = 0
            
            importData.resources.forEach { exportResource ->
                try {
                    val resource = exportResource.toResource()
                    
                    if (!resourceRepository.resourceExists(resource.url)) {
                        resourceRepository.addResource(resource)
                        importedResources++
                    } else {
                        skippedResources++
                    }
                } catch (e: Exception) {
                    skippedResources++
                }
            }
            
            val settings = importData.settings.toSettings()
            settingsRepository.saveSettings(settings)
            
            val result = ImportResult(
                importedResources = importedResources,
                skippedResources = skippedResources,
                totalResources = importData.resources.size
            )
            
            Result.success(result)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Экспорт только ресурсов
     */
    suspend fun exportResources(): Result<String> {
        return try {
            val resources = resourceRepository.getAllResourcesOnce()
            val exportResources = resources.map { it.toExportResource() }
            val jsonString = json.encodeToString(exportResources)
            Result.success(jsonString)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Импорт только ресурсов
     */
    suspend fun importResources(jsonString: String): Result<Int> {
        return try {
            val exportResources = json.decodeFromString<List<ExportResource>>(jsonString)
            
            var importedCount = 0
            exportResources.forEach { exportResource ->
                try {
                    val resource = exportResource.toResource()
                    if (!resourceRepository.resourceExists(resource.url)) {
                        resourceRepository.addResource(resource)
                        importedCount++
                    }
                } catch (e: Exception) {
                    // Пропуск невалидных ресурсов
                }
            }
            
            Result.success(importedCount)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // Data classes для сериализации
    
    @Serializable
    data class ExportData(
        val version: Int,
        val timestamp: Long,
        val resources: List<ExportResource>,
        val settings: ExportSettings
    )
    
    @Serializable
    data class ExportResource(
        val name: String,
        val url: String,
        val group: String,
        val enabled: Boolean
    )
    
    @Serializable
    data class ExportSettings(
        val themeMode: String,
        val checkIntervalMinutes: Int,
        val connectionTimeoutMs: Long,
        val enableNotifications: Boolean,
        val notifyOnFailure: Boolean,
        val notifyOnRecovery: Boolean,
        val notifyOnSlowResponse: Boolean,
        val slowResponseThresholdMs: Long,
        val historyRetentionDays: Int
    )
    
    data class ImportResult(
        val importedResources: Int,
        val skippedResources: Int,
        val totalResources: Int
    )
    
    // Extension functions
    
    private fun Resource.toExportResource(): ExportResource {
        return ExportResource(
            name = name,
            url = url,
            group = group.name,
            enabled = enabled
        )
    }
    
    private fun ExportResource.toResource(): Resource {
        return Resource(
            name = name,
            url = url,
            group = ResourceGroup.valueOf(group),
            enabled = enabled,
            createdAt = System.currentTimeMillis()
        )
    }
    
    private fun Settings.toExportSettings(): ExportSettings {
        return ExportSettings(
            themeMode = themeMode.name,
            checkIntervalMinutes = checkIntervalMinutes,
            connectionTimeoutMs = connectionTimeoutMs,
            enableNotifications = enableNotifications,
            notifyOnFailure = notifyOnFailure,
            notifyOnRecovery = notifyOnRecovery,
            notifyOnSlowResponse = notifyOnSlowResponse,
            slowResponseThresholdMs = slowResponseThresholdMs,
            historyRetentionDays = historyRetentionDays
        )
    }
    
    private fun ExportSettings.toSettings(): Settings {
        return Settings(
            themeMode = ThemeMode.valueOf(themeMode),
            checkIntervalMinutes = checkIntervalMinutes,
            connectionTimeoutMs = connectionTimeoutMs,
            enableNotifications = enableNotifications,
            notifyOnFailure = notifyOnFailure,
            notifyOnRecovery = notifyOnRecovery,
            notifyOnSlowResponse = notifyOnSlowResponse,
            slowResponseThresholdMs = slowResponseThresholdMs,
            historyRetentionDays = historyRetentionDays
        )
    }
}