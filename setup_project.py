#!/usr/bin/env python3
import os, shutil

BASE = "app/src/main"
JAVA = f"{BASE}/java/com/netweather"
RES = f"{BASE}/res"

print("🔧 SETUP NetWeather PROJECT")

# УДАЛЕНИЕ СТАРЫХ ФАЙЛОВ ИЗ КОРНЯ
for item in os.listdir(BASE):
    path = os.path.join(BASE, item)
    if os.path.isfile(path) and item != 'AndroidManifest.xml':
        os.remove(path)
        print(f"  🗑️  {item}")

# УДАЛЕНИЕ СТАРЫХ ПАПОК
for d in ['java/com/netweather/presentation/history', 'res/xml']:
    path = os.path.join(BASE, d)
    if os.path.exists(path):
        shutil.rmtree(path)

# СОЗДАНИЕ ПАПОК
dirs = [
    f"{JAVA}/domain/model", f"{JAVA}/domain/repository", f"{JAVA}/domain/usecase",
    f"{JAVA}/data/local/db/dao", f"{JAVA}/data/local/db/entity", f"{JAVA}/data/local/preferences",
    f"{JAVA}/data/remote", f"{JAVA}/data/repository", f"{JAVA}/di",
    f"{JAVA}/presentation/main/components", f"{JAVA}/presentation/history/components",
    f"{JAVA}/presentation/settings/components", f"{JAVA}/presentation/navigation",
    f"{JAVA}/presentation/theme", f"{JAVA}/worker", f"{JAVA}/notification", f"{JAVA}/widget",
    f"{RES}/values", f"{RES}/xml", f"{RES}/drawable", f"{RES}/layout", f"{RES}/mipmap-anydpi-v26",
]
for d in dirs:
    os.makedirs(d, exist_ok=True)

def w(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  📝 {path}")

# DOMAIN - MODELS
w(f"{JAVA}/domain/model/Resource.kt", '''package com.netweather.domain.model

data class Resource(
    val id: Long = 0, val name: String, val url: String,
    val group: ResourceGroup, val enabled: Boolean = true,
    val createdAt: Long = System.currentTimeMillis()
) {
    fun isValidUrl(): Boolean = url.isNotBlank() && (url.startsWith("http://") || url.startsWith("https://"))
}

enum class ResourceGroup { RU, INTL, CUSTOM }
''')

w(f"{JAVA}/domain/model/DiagnosticStatus.kt", '''package com.netweather.domain.model

enum class DiagnosticStatus {
    OK, DNS_ERROR, TCP_ERROR, TLS_ERROR, HTTP_ERROR, TIMEOUT, CONTENT_ERROR, UNKNOWN_ERROR;
    fun isSuccessful(): Boolean = this == OK
    fun getDescription(): String = when (this) {
        OK -> "OK"; DNS_ERROR -> "DNS error"; TCP_ERROR -> "TCP error"
        TLS_ERROR -> "TLS error"; HTTP_ERROR -> "HTTP error"; TIMEOUT -> "Timeout"
        CONTENT_ERROR -> "Content error"; UNKNOWN_ERROR -> "Unknown error"
    }
}
''')

w(f"{JAVA}/domain/model/CheckResult.kt", '''package com.netweather.domain.model

data class CheckResult(
    val id: Long = 0, val resourceId: Long, val timestamp: Long = System.currentTimeMillis(),
    val dnsStatus: DiagnosticStatus, val tcpStatus: DiagnosticStatus, val tlsStatus: DiagnosticStatus,
    val httpStatus: DiagnosticStatus, val contentStatus: DiagnosticStatus,
    val responseTimeMs: Long, val errorMessage: String? = null
) {
    fun isSuccessful(): Boolean = dnsStatus == DiagnosticStatus.OK && tcpStatus == DiagnosticStatus.OK && tlsStatus == DiagnosticStatus.OK && httpStatus == DiagnosticStatus.OK && contentStatus == DiagnosticStatus.OK
    fun getFirstErrorStatus(): DiagnosticStatus = when {
        dnsStatus != DiagnosticStatus.OK -> dnsStatus; tcpStatus != DiagnosticStatus.OK -> tcpStatus
        tlsStatus != DiagnosticStatus.OK -> tlsStatus; httpStatus != DiagnosticStatus.OK -> httpStatus
        contentStatus != DiagnosticStatus.OK -> contentStatus; else -> DiagnosticStatus.OK
    }
    fun getErrorDescription(): String = getFirstErrorStatus().getDescription()
}
''')

w(f"{JAVA}/domain/model/NetworkMode.kt", '''package com.netweather.domain.model

enum class NetworkMode {
    NORMAL, PARTIAL_DEGRADATION, RESTRICTED_ACCESS, NO_INTERNET;
    fun getEmoji(): String = when (this) { NORMAL -> "🟢"; PARTIAL_DEGRADATION -> "🟡"; RESTRICTED_ACCESS -> "🟠"; NO_INTERNET -> "🔴" }
    fun getTitle(): String = when (this) { NORMAL -> "Normal"; PARTIAL_DEGRADATION -> "Partial"; RESTRICTED_ACCESS -> "Restricted"; NO_INTERNET -> "No internet" }
    fun getShortDescription(): String = when (this) { NORMAL -> "All OK"; PARTIAL_DEGRADATION -> "Some issues"; RESTRICTED_ACCESS -> "Restricted"; NO_INTERNET -> "No internet" }
}
''')

w(f"{JAVA}/domain/model/AvailabilityIndex.kt", '''package com.netweather.domain.model

data class AvailabilityIndex(val value: Int) {
    companion object { fun create(value: Int): AvailabilityIndex = AvailabilityIndex(value.coerceIn(0, 100)) }
}
''')

w(f"{JAVA}/domain/model/HistoryEntry.kt", '''package com.netweather.domain.model

data class HistoryEntry(
    val id: Long = 0, val timestamp: Long = System.currentTimeMillis(),
    val availabilityIndex: Int, val networkMode: NetworkMode,
    val availableCount: Int, val unavailableCount: Int, val details: String = ""
)

enum class HistoryPeriod {
    HOUR, DAY, WEEK;
    fun getDurationMs(): Long = when (this) { HOUR -> 3600000L; DAY -> 86400000L; WEEK -> 604800000L }
    fun getTitle(): String = when (this) { HOUR -> "1h"; DAY -> "24h"; WEEK -> "7d" }
}
''')

w(f"{JAVA}/domain/model/NetworkState.kt", '''package com.netweather.domain.model

data class NetworkState(
    val availabilityIndex: AvailabilityIndex, val networkMode: NetworkMode, val lastCheckTime: Long,
    val availableCount: Int, val unavailableCount: Int, val totalResources: Int,
    val resourceStates: Map<ResourceGroup, List<ResourceState>> = emptyMap()
)

data class ResourceState(
    val resource: Resource, val lastCheckResult: CheckResult?,
    val isAvailable: Boolean, val responseTimeMs: Long = 0, val lastCheckTime: Long = 0
) {
    fun getDiagnosticStatus(): DiagnosticStatus = lastCheckResult?.getFirstErrorStatus() ?: DiagnosticStatus.UNKNOWN_ERROR
    fun getErrorDescription(): String = lastCheckResult?.getErrorDescription() ?: "No data"
}
''')

w(f"{JAVA}/domain/model/Settings.kt", '''package com.netweather.domain.model

data class Settings(
    val themeMode: ThemeMode = ThemeMode.SYSTEM,
    val checkIntervalMinutes: Int = 15,
    val connectionTimeoutMs: Long = 10000L,
    val enableNotifications: Boolean = true,
    val notifyOnFailure: Boolean = true,
    val notifyOnRecovery: Boolean = true,
    val notifyOnSlowResponse: Boolean = false,
    val slowResponseThresholdMs: Long = 5000L,
    val historyRetentionDays: Int = 7,
    val enableWidgetsEnabled: Boolean = true
)

enum class ThemeMode {
    LIGHT, DARK, SYSTEM;
    fun getTitle(): String = when (this) { LIGHT -> "Light"; DARK -> "Dark"; SYSTEM -> "System" }
}
''')

# DOMAIN - REPOSITORIES
w(f"{JAVA}/domain/repository/ResourceRepository.kt", '''package com.netweather.domain.repository

import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import kotlinx.coroutines.flow.Flow

interface ResourceRepository {
    fun getAllResources(): Flow<List<Resource>>
    fun getResourcesByGroup(group: ResourceGroup): Flow<List<Resource>>
    fun getEnabledResources(): Flow<List<Resource>>
    suspend fun getResourceById(id: Long): Resource?
    suspend fun addResource(resource: Resource): Long
    suspend fun updateResource(resource: Resource)
    suspend fun deleteResource(id: Long)
    suspend fun setResourceEnabled(id: Long, enabled: Boolean)
    suspend fun resourceExists(url: String): Boolean
    suspend fun getResourceCount(group: ResourceGroup): Int
    suspend fun getTotalResourceCount(): Int
    suspend fun initializeDefaultResources()
    suspend fun deleteAllResources()
    suspend fun getAllResourcesOnce(): List<Resource>
}
''')

w(f"{JAVA}/domain/repository/DiagnosticsRepository.kt", '''package com.netweather.domain.repository

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import kotlinx.coroutines.flow.Flow

interface DiagnosticsRepository {
    suspend fun checkResource(resource: Resource): CheckResult
    suspend fun saveCheckResult(result: CheckResult): Long
    suspend fun getLastCheckResult(resourceId: Long): CheckResult?
    fun getLastCheckResults(): Flow<List<CheckResult>>
    suspend fun getLastCheckResultsOnce(): List<CheckResult>
    suspend fun getCheckHistory(resourceId: Long, limit: Int = 100): List<CheckResult>
    suspend fun deleteOldCheckResults(olderThanMs: Long): Int
    suspend fun deleteAllCheckResults()
    suspend fun getAverageResponseTime(resourceId: Long, periodMs: Long = 3600000L): Long
    suspend fun isResourceAvailable(resource: Resource): Boolean
}
''')

w(f"{JAVA}/domain/repository/HistoryRepository.kt", '''package com.netweather.domain.repository

import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import kotlinx.coroutines.flow.Flow

interface HistoryRepository {
    suspend fun saveHistoryEntry(entry: HistoryEntry): Long
    fun getHistory(period: HistoryPeriod): Flow<List<HistoryEntry>>
    suspend fun getHistoryOnce(period: HistoryPeriod): List<HistoryEntry>
    suspend fun getLastHistoryEntry(): HistoryEntry?
    suspend fun deleteOldHistory(olderThanMs: Long): Int
    suspend fun deleteAllHistory()
    suspend fun getHistoryCount(): Int
    suspend fun getStatistics(period: HistoryPeriod): Map<String, Any>
    suspend fun getAverageAvailabilityIndex(period: HistoryPeriod): Int
    suspend fun getMinAvailabilityIndex(period: HistoryPeriod): Int
    suspend fun getMaxAvailabilityIndex(period: HistoryPeriod): Int
}
''')

w(f"{JAVA}/domain/repository/SettingsRepository.kt", '''package com.netweather.domain.repository

import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import kotlinx.coroutines.flow.Flow

interface SettingsRepository {
    fun getSettings(): Flow<Settings>
    suspend fun getSettingsOnce(): Settings
    suspend fun saveSettings(settings: Settings)
    suspend fun setThemeMode(themeMode: ThemeMode)
    suspend fun setCheckInterval(minutes: Int)
    suspend fun setNotificationsEnabled(enabled: Boolean)
    suspend fun setNotifyOnFailure(enabled: Boolean)
    suspend fun setNotifyOnRecovery(enabled: Boolean)
    suspend fun setNotifyOnSlowResponse(enabled: Boolean)
    suspend fun setHistoryRetentionDays(days: Int)
    suspend fun resetToDefaults()
}
''')

# DOMAIN - USE CASES
w(f"{JAVA}/domain/usecase/CheckResourceUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import com.netweather.domain.repository.DiagnosticsRepository
import javax.inject.Inject

class CheckResourceUseCase @Inject constructor(private val diagnosticsRepository: DiagnosticsRepository) {
    suspend operator fun invoke(resource: Resource): Result<CheckResult> = try {
        val result = diagnosticsRepository.checkResource(resource)
        diagnosticsRepository.saveCheckResult(result)
        Result.success(result)
    } catch (e: Exception) { Result.failure(e) }
}
''')

w(f"{JAVA}/domain/usecase/CheckAllResourcesUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.ResourceRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import javax.inject.Inject

class CheckAllResourcesUseCase @Inject constructor(
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository
) {
    suspend operator fun invoke(): Result<List<CheckResult>> = try {
        val resources = resourceRepository.getAllResourcesOnce().filter { it.enabled }
        if (resources.isEmpty()) return Result.success(emptyList())
        val results = coroutineScope {
            resources.map { r -> async {
                try {
                    val result = diagnosticsRepository.checkResource(r)
                    diagnosticsRepository.saveCheckResult(result)
                    result
                } catch (e: Exception) {
                    CheckResult(resourceId = r.id, dnsStatus = DiagnosticStatus.UNKNOWN_ERROR, tcpStatus = DiagnosticStatus.UNKNOWN_ERROR, tlsStatus = DiagnosticStatus.UNKNOWN_ERROR, httpStatus = DiagnosticStatus.UNKNOWN_ERROR, contentStatus = DiagnosticStatus.UNKNOWN_ERROR, responseTimeMs = 0, errorMessage = e.message)
                }
            }}.awaitAll()
        }
        Result.success(results)
    } catch (e: Exception) { Result.failure(e) }
    
    suspend fun checkAllOnce(): Result<List<CheckResult>> = invoke()
}
''')

w(f"{JAVA}/domain/usecase/CalculateAvailabilityIndexUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import javax.inject.Inject

class CalculateAvailabilityIndexUseCase @Inject constructor() {
    suspend operator fun invoke(resources: List<Resource>, checkResults: List<CheckResult>): Result<AvailabilityIndex> = try {
        if (resources.isEmpty()) return Result.success(AvailabilityIndex.create(0))
        val resultsMap = checkResults.associateBy { it.resourceId }
        val availableCount = resources.count { r -> resultsMap[r.id]?.isSuccessful() == true }
        val index = (availableCount * 100) / resources.size
        Result.success(AvailabilityIndex.create(index))
    } catch (e: Exception) { Result.failure(e) }
}
''')

w(f"{JAVA}/domain/usecase/DetermineNetworkModeUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.Resource
import javax.inject.Inject

class DetermineNetworkModeUseCase @Inject constructor() {
    suspend operator fun invoke(index: AvailabilityIndex, resources: List<Resource>, results: List<CheckResult>): Result<NetworkMode> = try {
        val mode = when {
            index.value >= 80 -> NetworkMode.NORMAL
            index.value >= 70 -> NetworkMode.PARTIAL_DEGRADATION
            index.value < 30 -> NetworkMode.NO_INTERNET
            else -> NetworkMode.PARTIAL_DEGRADATION
        }
        Result.success(mode)
    } catch (e: Exception) { Result.failure(e) }
}
''')

w(f"{JAVA}/domain/usecase/GetHistoryUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.domain.repository.HistoryRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetHistoryUseCase @Inject constructor(private val historyRepository: HistoryRepository) {
    operator fun invoke(period: HistoryPeriod): Flow<List<HistoryEntry>> = historyRepository.getHistory(period)
    suspend fun getOnce(period: HistoryPeriod): Result<List<HistoryEntry>> = try { Result.success(historyRepository.getHistoryOnce(period)) } catch (e: Exception) { Result.failure(e) }
}
''')

w(f"{JAVA}/domain/usecase/AddResourceUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.repository.ResourceRepository
import javax.inject.Inject

class AddResourceUseCase @Inject constructor(private val resourceRepository: ResourceRepository) {
    suspend operator fun invoke(name: String, url: String, group: ResourceGroup): Result<Long> = try {
        if (name.isBlank()) return Result.failure(IllegalArgumentException("Name is empty"))
        val normalizedUrl = if (url.startsWith("http://") || url.startsWith("https://")) url else "https://$url"
        if (resourceRepository.resourceExists(normalizedUrl)) return Result.failure(IllegalStateException("Resource exists"))
        val resource = Resource(name = name.trim(), url = normalizedUrl, group = group, enabled = true)
        Result.success(resourceRepository.addResource(resource))
    } catch (e: Exception) { Result.failure(e) }
}
''')

w(f"{JAVA}/domain/usecase/DeleteResourceUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.repository.ResourceRepository
import javax.inject.Inject

class DeleteResourceUseCase @Inject constructor(private val resourceRepository: ResourceRepository) {
    suspend operator fun invoke(id: Long): Result<Unit> = try {
        resourceRepository.deleteResource(id)
        Result.success(Unit)
    } catch (e: Exception) { Result.failure(e) }
}
''')

w(f"{JAVA}/domain/usecase/ExportImportUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import javax.inject.Inject

class ExportImportUseCase @Inject constructor(
    private val resourceRepository: ResourceRepository,
    private val settingsRepository: SettingsRepository
) {
    suspend fun exportData(): Result<String> = try {
        val resources = resourceRepository.getAllResourcesOnce()
        Result.success(resources.joinToString("\\n") { "${it.name}|${it.url}|${it.group}" })
    } catch (e: Exception) { Result.failure(e) }
}
''')

print("✅ Domain layer created")

# DATA - LOCAL DB
w(f"{JAVA}/data/local/db/AppDatabase.kt", '''package com.netweather.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.netweather.data.local.db.dao.CheckResultDao
import com.netweather.data.local.db.dao.HistoryDao
import com.netweather.data.local.db.dao.ResourceDao
import com.netweather.data.local.db.entity.CheckResultEntity
import com.netweather.data.local.db.entity.HistoryEntity
import com.netweather.data.local.db.entity.ResourceEntity

@Database(entities = [ResourceEntity::class, CheckResultEntity::class, HistoryEntity::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun resourceDao(): ResourceDao
    abstract fun checkResultDao(): CheckResultDao
    abstract fun historyDao(): HistoryDao
}
''')

w(f"{JAVA}/data/local/db/dao/ResourceDao.kt", '''package com.netweather.data.local.db.dao

import androidx.room.*
import com.netweather.data.local.db.entity.ResourceEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ResourceDao {
    @Query("SELECT * FROM resources ORDER BY created_at DESC")
    fun getAllResources(): Flow<List<ResourceEntity>>
    
    @Query("SELECT * FROM resources ORDER BY created_at DESC")
    suspend fun getAllResourcesOnce(): List<ResourceEntity>
    
    @Query("SELECT * FROM resources WHERE `group` = :group ORDER BY name ASC")
    fun getResourcesByGroup(group: String): Flow<List<ResourceEntity>>
    
    @Query("SELECT * FROM resources WHERE enabled = 1 ORDER BY `group`, name ASC")
    fun getEnabledResources(): Flow<List<ResourceEntity>>
    
    @Query("SELECT * FROM resources WHERE id = :id LIMIT 1")
    suspend fun getResourceById(id: Long): ResourceEntity?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertResource(resource: ResourceEntity): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertResources(resources: List<ResourceEntity>): List<Long>
    
    @Update
    suspend fun updateResource(resource: ResourceEntity)
    
    @Query("DELETE FROM resources WHERE id = :id")
    suspend fun deleteResourceById(id: Long)
    
    @Query("UPDATE resources SET enabled = :enabled WHERE id = :id")
    suspend fun setResourceEnabled(id: Long, enabled: Boolean)
    
    @Query("SELECT EXISTS(SELECT 1 FROM resources WHERE url = :url)")
    suspend fun resourceExists(url: String): Boolean
    
    @Query("SELECT COUNT(*) FROM resources WHERE `group` = :group")
    suspend fun getResourceCount(group: String): Int
    
    @Query("SELECT COUNT(*) FROM resources")
    suspend fun getTotalResourceCount(): Int
    
    @Query("DELETE FROM resources")
    suspend fun deleteAllResources()
}
''')

w(f"{JAVA}/data/local/db/dao/CheckResultDao.kt", '''package com.netweather.data.local.db.dao

import androidx.room.*
import com.netweather.data.local.db.entity.CheckResultEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface CheckResultDao {
    @Query("SELECT * FROM check_results WHERE resource_id = :resourceId ORDER BY timestamp DESC LIMIT 1")
    suspend fun getLastCheckResult(resourceId: Long): CheckResultEntity?
    
    @Query("SELECT cr.* FROM check_results cr INNER JOIN (SELECT resource_id, MAX(timestamp) as max_timestamp FROM check_results GROUP BY resource_id) latest ON cr.resource_id = latest.resource_id AND cr.timestamp = latest.max_timestamp ORDER BY cr.timestamp DESC")
    fun getLastCheckResults(): Flow<List<CheckResultEntity>>
    
    @Query("SELECT cr.* FROM check_results cr INNER JOIN (SELECT resource_id, MAX(timestamp) as max_timestamp FROM check_results GROUP BY resource_id) latest ON cr.resource_id = latest.resource_id AND cr.timestamp = latest.max_timestamp ORDER BY cr.timestamp DESC")
    suspend fun getLastCheckResultsOnce(): List<CheckResultEntity>
    
    @Query("SELECT * FROM check_results WHERE resource_id = :resourceId ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getCheckHistory(resourceId: Long, limit: Int = 100): List<CheckResultEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCheckResult(checkResult: CheckResultEntity): Long
    
    @Query("DELETE FROM check_results WHERE timestamp < :olderThan")
    suspend fun deleteOldCheckResults(olderThan: Long): Int
    
    @Query("DELETE FROM check_results")
    suspend fun deleteAllCheckResults()
    
    @Query("SELECT AVG(response_time_ms) FROM check_results WHERE resource_id = :resourceId AND timestamp > :sinceTimestamp")
    suspend fun getAverageResponseTime(resourceId: Long, sinceTimestamp: Long): Long?
}
''')

w(f"{JAVA}/data/local/db/dao/HistoryDao.kt", '''package com.netweather.data.local.db.dao

import androidx.room.*
import com.netweather.data.local.db.entity.HistoryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface HistoryDao {
    @Query("SELECT * FROM history WHERE timestamp > :sinceTimestamp ORDER BY timestamp DESC")
    fun getHistorySince(sinceTimestamp: Long): Flow<List<HistoryEntity>>
    
    @Query("SELECT * FROM history WHERE timestamp > :sinceTimestamp ORDER BY timestamp DESC")
    suspend fun getHistorySinceOnce(sinceTimestamp: Long): List<HistoryEntity>
    
    @Query("SELECT * FROM history ORDER BY timestamp DESC LIMIT 1")
    suspend fun getLastHistoryEntry(): HistoryEntity?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertHistoryEntry(historyEntry: HistoryEntity): Long
    
    @Query("DELETE FROM history WHERE timestamp < :olderThan")
    suspend fun deleteOldHistory(olderThan: Long): Int
    
    @Query("DELETE FROM history")
    suspend fun deleteAllHistory()
    
    @Query("SELECT COUNT(*) FROM history")
    suspend fun getHistoryCount(): Int
    
    @Query("SELECT AVG(availability_index) FROM history WHERE timestamp > :sinceTimestamp")
    suspend fun getAverageAvailabilityIndex(sinceTimestamp: Long): Int?
    
    @Query("SELECT MIN(availability_index) FROM history WHERE timestamp > :sinceTimestamp")
    suspend fun getMinAvailabilityIndex(sinceTimestamp: Long): Int?
    
    @Query("SELECT MAX(availability_index) FROM history WHERE timestamp > :sinceTimestamp")
    suspend fun getMaxAvailabilityIndex(sinceTimestamp: Long): Int?
    
    @Query("SELECT COUNT(*) FROM history WHERE network_mode = :networkMode AND timestamp > :sinceTimestamp")
    suspend fun getCountByNetworkMode(networkMode: String, sinceTimestamp: Long): Int
}
''')

w(f"{JAVA}/data/local/db/entity/ResourceEntity.kt", '''package com.netweather.data.local.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup

@Entity(tableName = "resources")
data class ResourceEntity(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "id") val id: Long = 0,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "url") val url: String,
    @ColumnInfo(name = "group") val group: String,
    @ColumnInfo(name = "enabled") val enabled: Boolean = true,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis()
) {
    fun toDomain(): Resource = Resource(id = id, name = name, url = url, group = ResourceGroup.valueOf(group), enabled = enabled, createdAt = createdAt)
    companion object { fun fromDomain(r: Resource): ResourceEntity = ResourceEntity(id = r.id, name = r.name, url = r.url, group = r.group.name, enabled = r.enabled, createdAt = r.createdAt) }
}
''')

w(f"{JAVA}/data/local/db/entity/CheckResultEntity.kt", '''package com.netweather.data.local.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus

@Entity(tableName = "check_results", foreignKeys = [ForeignKey(entity = ResourceEntity::class, parentColumns = ["id"], childColumns = ["resource_id"], onDelete = ForeignKey.CASCADE)], indices = [Index(value = ["resource_id"]), Index(value = ["timestamp"])])
data class CheckResultEntity(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "id") val id: Long = 0,
    @ColumnInfo(name = "resource_id") val resourceId: Long,
    @ColumnInfo(name = "timestamp") val timestamp: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "dns_status") val dnsStatus: String,
    @ColumnInfo(name = "tcp_status") val tcpStatus: String,
    @ColumnInfo(name = "tls_status") val tlsStatus: String,
    @ColumnInfo(name = "http_status") val httpStatus: String,
    @ColumnInfo(name = "content_status") val contentStatus: String,
    @ColumnInfo(name = "response_time_ms") val responseTimeMs: Long,
    @ColumnInfo(name = "error_message") val errorMessage: String? = null
) {
    fun toDomain(): CheckResult = CheckResult(id = id, resourceId = resourceId, timestamp = timestamp, dnsStatus = DiagnosticStatus.valueOf(dnsStatus), tcpStatus = DiagnosticStatus.valueOf(tcpStatus), tlsStatus = DiagnosticStatus.valueOf(tlsStatus), httpStatus = DiagnosticStatus.valueOf(httpStatus), contentStatus = DiagnosticStatus.valueOf(contentStatus), responseTimeMs = responseTimeMs, errorMessage = errorMessage)
    companion object { fun fromDomain(c: CheckResult): CheckResultEntity = CheckResultEntity(id = c.id, resourceId = c.resourceId, timestamp = c.timestamp, dnsStatus = c.dnsStatus.name, tcpStatus = c.tcpStatus.name, tlsStatus = c.tlsStatus.name, httpStatus = c.httpStatus.name, contentStatus = c.contentStatus.name, responseTimeMs = c.responseTimeMs, errorMessage = c.errorMessage) }
}
''')

w(f"{JAVA}/data/local/db/entity/HistoryEntity.kt", '''package com.netweather.data.local.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.NetworkMode

@Entity(tableName = "history", indices = [Index(value = ["timestamp"])])
data class HistoryEntity(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "id") val id: Long = 0,
    @ColumnInfo(name = "timestamp") val timestamp: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "availability_index") val availabilityIndex: Int,
    @ColumnInfo(name = "network_mode") val networkMode: String,
    @ColumnInfo(name = "available_count") val availableCount: Int,
    @ColumnInfo(name = "unavailable_count") val unavailableCount: Int,
    @ColumnInfo(name = "details") val details: String = ""
) {
    fun toDomain(): HistoryEntry = HistoryEntry(id = id, timestamp = timestamp, availabilityIndex = availabilityIndex, networkMode = NetworkMode.valueOf(networkMode), availableCount = availableCount, unavailableCount = unavailableCount, details = details)
    companion object { fun fromDomain(h: HistoryEntry): HistoryEntity = HistoryEntity(id = h.id, timestamp = h.timestamp, availabilityIndex = h.availabilityIndex, networkMode = h.networkMode.name, availableCount = h.availableCount, unavailableCount = h.unavailableCount, details = h.details) }
}
''')

w(f"{JAVA}/data/local/preferences/PreferencesManager.kt", '''package com.netweather.data.local.preferences

import android.content.Context
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PreferencesManager @Inject constructor(@ApplicationContext private val context: Context) {
    private val Context.dataStore by preferencesDataStore(name = "netweather_prefs")
    
    fun getSettings(): Flow<Settings> = context.dataStore.data.map { p ->
        Settings(
            themeMode = try { ThemeMode.valueOf(p[stringPreferencesKey("theme_mode")] ?: ThemeMode.SYSTEM.name) } catch (e: Exception) { ThemeMode.SYSTEM },
            checkIntervalMinutes = p[intPreferencesKey("check_interval")] ?: 15,
            enableNotifications = p[booleanPreferencesKey("enable_notifications")] ?: true,
            notifyOnFailure = p[booleanPreferencesKey("notify_on_failure")] ?: true,
            notifyOnRecovery = p[booleanPreferencesKey("notify_on_recovery")] ?: true,
            notifyOnSlowResponse = p[booleanPreferencesKey("notify_on_slow")] ?: false,
            historyRetentionDays = p[intPreferencesKey("history_retention")] ?: 7
        )
    }
    
    suspend fun saveSettings(settings: Settings) {
        context.dataStore.edit { p ->
            p[stringPreferencesKey("theme_mode")] = settings.themeMode.name
            p[intPreferencesKey("check_interval")] = settings.checkIntervalMinutes
            p[booleanPreferencesKey("enable_notifications")] = settings.enableNotifications
            p[booleanPreferencesKey("notify_on_failure")] = settings.notifyOnFailure
            p[booleanPreferencesKey("notify_on_recovery")] = settings.notifyOnRecovery
            p[booleanPreferencesKey("notify_on_slow")] = settings.notifyOnSlowResponse
            p[intPreferencesKey("history_retention")] = settings.historyRetentionDays
        }
    }
    
    suspend fun setThemeMode(m: ThemeMode) { context.dataStore.edit { it[stringPreferencesKey("theme_mode")] = m.name } }
    suspend fun setCheckInterval(m: Int) { context.dataStore.edit { it[intPreferencesKey("check_interval")] = m } }
    suspend fun setNotificationsEnabled(e: Boolean) { context.dataStore.edit { it[booleanPreferencesKey("enable_notifications")] = e } }
    suspend fun setNotifyOnFailure(e: Boolean) { context.dataStore.edit { it[booleanPreferencesKey("notify_on_failure")] = e } }
    suspend fun setNotifyOnRecovery(e: Boolean) { context.dataStore.edit { it[booleanPreferencesKey("notify_on_recovery")] = e } }
    suspend fun setNotifyOnSlowResponse(e: Boolean) { context.dataStore.edit { it[booleanPreferencesKey("notify_on_slow")] = e } }
    suspend fun setHistoryRetentionDays(d: Int) { context.dataStore.edit { it[intPreferencesKey("history_retention")] = d } }
    suspend fun resetToDefaults() { context.dataStore.edit { it.clear() } }
}
''')

print("✅ Data local layer created")

# DATA - REMOTE
w(f"{JAVA}/data/remote/NetworkClient.kt", '''package com.netweather.data.remote

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NetworkClient @Inject constructor() {
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .followRedirects(true)
        .followSslRedirects(true)
        .build()
    
    fun executeGet(url: String): Response {
        val request = Request.Builder().url(url).get().build()
        return client.newCall(request).execute()
    }
    
    fun executeHead(url: String): Response {
        val request = Request.Builder().url(url).head().build()
        return client.newCall(request).execute()
    }
}
''')

w(f"{JAVA}/data/remote/NetworkDiagnostics.kt", '''package com.netweather.data.remote

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.DiagnosticStatus
import com.netweather.domain.model.Resource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.InetAddress
import java.net.Socket
import java.net.URL
import java.net.UnknownHostException
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NetworkDiagnostics @Inject constructor(private val networkClient: NetworkClient) {
    
    suspend fun performFullDiagnostics(resource: Resource, timeoutMs: Long = 10000L): CheckResult = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        try {
            val url = URL(resource.url)
            val host = url.host
            val port = if (url.port != -1) url.port else if (url.protocol == "https") 443 else 80
            val isHttps = url.protocol == "https"
            
            val dnsResult = checkDns(host, timeoutMs)
            if (dnsResult != DiagnosticStatus.OK) return@withContext createResult(resource, startTime, dnsResult, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, "DNS failed")
            
            val tcpResult = checkTcp(host, port, timeoutMs)
            if (tcpResult != DiagnosticStatus.OK) return@withContext createResult(resource, startTime, dnsResult, tcpResult, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, "TCP failed")
            
            val tlsResult = if (isHttps) checkTls(host, port, timeoutMs) else DiagnosticStatus.OK
            if (tlsResult != DiagnosticStatus.OK) return@withContext createResult(resource, startTime, dnsResult, tcpResult, tlsResult, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, "TLS failed")
            
            val httpResult = checkHttp(resource.url)
            if (httpResult.first != DiagnosticStatus.OK) return@withContext createResult(resource, startTime, dnsResult, tcpResult, tlsResult, httpResult.first, DiagnosticStatus.UNKNOWN_ERROR, httpResult.second)
            
            val contentResult = checkContent(httpResult.second)
            createResult(resource, startTime, dnsResult, tcpResult, tlsResult, httpResult.first, contentResult, if (contentResult != DiagnosticStatus.OK) "Content failed" else null)
        } catch (e: Exception) {
            createResult(resource, startTime, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, DiagnosticStatus.UNKNOWN_ERROR, e.message)
        }
    }
    
    suspend fun isAvailable(resource: Resource): Boolean = withContext(Dispatchers.IO) {
        try {
            val response = networkClient.executeHead(resource.url)
            response.use { it.isSuccessful }
        } catch (e: Exception) { false }
    }
    
    private fun checkDns(host: String, timeoutMs: Long): DiagnosticStatus {
        return try {
            val thread = Thread { InetAddress.getAllByName(host) }
            thread.start()
            thread.join(timeoutMs)
            if (thread.isAlive) { thread.interrupt(); DiagnosticStatus.TIMEOUT } else DiagnosticStatus.OK
        } catch (e: UnknownHostException) { DiagnosticStatus.DNS_ERROR } catch (e: Exception) { DiagnosticStatus.UNKNOWN_ERROR }
    }
    
    private fun checkTcp(host: String, port: Int, timeoutMs: Long): DiagnosticStatus {
        var socket: Socket? = null
        return try {
            socket = Socket()
            socket.soTimeout = timeoutMs.toInt()
            socket.connect(java.net.InetSocketAddress(host, port), timeoutMs.toInt())
            DiagnosticStatus.OK
        } catch (e: Exception) { DiagnosticStatus.TCP_ERROR } finally { try { socket?.close() } catch (_: Exception) {} }
    }
    
    private fun checkTls(host: String, port: Int, timeoutMs: Long): DiagnosticStatus {
        var socket: javax.net.ssl.SSLSocket? = null
        return try {
            val sslContext = javax.net.ssl.SSLContext.getInstance("TLS")
            sslContext.init(null, null, null)
            socket = sslContext.socketFactory.createSocket(host, port) as javax.net.ssl.SSLSocket
            socket.soTimeout = timeoutMs.toInt()
            socket.startHandshake()
            DiagnosticStatus.OK
        } catch (e: Exception) { DiagnosticStatus.TLS_ERROR } finally { try { socket?.close() } catch (_: Exception) {} }
    }
    
    private fun checkHttp(url: String): Pair<DiagnosticStatus, okhttp3.Response?> {
        return try {
            val response = networkClient.executeGet(url)
            if (response.isSuccessful || response.code in 300..399) Pair(DiagnosticStatus.OK, response) else Pair(DiagnosticStatus.HTTP_ERROR, response)
        } catch (e: Exception) { Pair(DiagnosticStatus.HTTP_ERROR, null) }
    }
    
    private fun checkContent(response: okhttp3.Response?): DiagnosticStatus {
        if (response == null || response.body == null) return DiagnosticStatus.CONTENT_ERROR
        return try {
            val body = response.body!!
            if (body.contentLength() > 0 && body.contentLength() < 100) DiagnosticStatus.CONTENT_ERROR else DiagnosticStatus.OK
        } catch (e: Exception) { DiagnosticStatus.CONTENT_ERROR }
    }
    
    private fun createResult(resource: Resource, startTime: Long, dns: DiagnosticStatus, tcp: DiagnosticStatus, tls: DiagnosticStatus, http: DiagnosticStatus, content: DiagnosticStatus, error: String?): CheckResult {
        return CheckResult(resourceId = resource.id, timestamp = System.currentTimeMillis(), dnsStatus = dns, tcpStatus = tcp, tlsStatus = tls, httpStatus = http, contentStatus = content, responseTimeMs = System.currentTimeMillis() - startTime, errorMessage = error)
    }
}
''')

print("✅ Data remote layer created")

# DATA - REPOSITORIES
w(f"{JAVA}/data/repository/ResourceRepositoryImpl.kt", '''package com.netweather.data.repository

import com.netweather.data.local.db.dao.ResourceDao
import com.netweather.data.local.db.entity.ResourceEntity
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.repository.ResourceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ResourceRepositoryImpl @Inject constructor(private val resourceDao: ResourceDao) : ResourceRepository {
    override fun getAllResources(): Flow<List<Resource>> = resourceDao.getAllResources().map { it.map { e -> e.toDomain() } }
    override fun getResourcesByGroup(group: ResourceGroup): Flow<List<Resource>> = resourceDao.getResourcesByGroup(group.name).map { it.map { e -> e.toDomain() } }
    override fun getEnabledResources(): Flow<List<Resource>> = resourceDao.getEnabledResources().map { it.map { e -> e.toDomain() } }
    override suspend fun getResourceById(id: Long): Resource? = resourceDao.getResourceById(id)?.toDomain()
    override suspend fun addResource(resource: Resource): Long = resourceDao.insertResource(ResourceEntity.fromDomain(resource))
    override suspend fun updateResource(resource: Resource) = resourceDao.updateResource(ResourceEntity.fromDomain(resource))
    override suspend fun deleteResource(id: Long) = resourceDao.deleteResourceById(id)
    override suspend fun setResourceEnabled(id: Long, enabled: Boolean) = resourceDao.setResourceEnabled(id, enabled)
    override suspend fun resourceExists(url: String): Boolean = resourceDao.resourceExists(url)
    override suspend fun getResourceCount(group: ResourceGroup): Int = resourceDao.getResourceCount(group.name)
    override suspend fun getTotalResourceCount(): Int = resourceDao.getTotalResourceCount()
    override suspend fun deleteAllResources() = resourceDao.deleteAllResources()
    override suspend fun getAllResourcesOnce(): List<Resource> = resourceDao.getAllResourcesOnce().map { it.toDomain() }
    
    override suspend fun initializeDefaultResources() {
        if (resourceDao.getTotalResourceCount() > 0) return
        val defaults = listOf(
            Resource(name = "Yandex", url = "https://yandex.ru", group = ResourceGroup.RU),
            Resource(name = "VK", url = "https://vk.com", group = ResourceGroup.RU),
            Resource(name = "Gosuslugi", url = "https://gosuslugi.ru", group = ResourceGroup.RU),
            Resource(name = "Mail.ru", url = "https://mail.ru", group = ResourceGroup.RU),
            Resource(name = "Rutube", url = "https://rutube.ru", group = ResourceGroup.RU),
            Resource(name = "YouTube", url = "https://youtube.com", group = ResourceGroup.INTL),
            Resource(name = "Reddit", url = "https://reddit.com", group = ResourceGroup.INTL),
            Resource(name = "Instagram", url = "https://instagram.com", group = ResourceGroup.INTL),
            Resource(name = "Telegram", url = "https://telegram.org", group = ResourceGroup.INTL),
            Resource(name = "Discord", url = "https://discord.com", group = ResourceGroup.INTL),
            Resource(name = "GitHub", url = "https://github.com", group = ResourceGroup.INTL),
            Resource(name = "Wikipedia", url = "https://wikipedia.org", group = ResourceGroup.INTL)
        )
        resourceDao.insertResources(defaults.map { ResourceEntity.fromDomain(it) })
    }
}
''')

w(f"{JAVA}/data/repository/DiagnosticsRepositoryImpl.kt", '''package com.netweather.data.repository

import com.netweather.data.local.db.dao.CheckResultDao
import com.netweather.data.local.db.entity.CheckResultEntity
import com.netweather.data.remote.NetworkDiagnostics
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import com.netweather.domain.repository.DiagnosticsRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DiagnosticsRepositoryImpl @Inject constructor(
    private val checkResultDao: CheckResultDao,
    private val networkDiagnostics: NetworkDiagnostics
) : DiagnosticsRepository {
    override suspend fun checkResource(resource: Resource): CheckResult = networkDiagnostics.performFullDiagnostics(resource)
    override suspend fun saveCheckResult(result: CheckResult): Long = checkResultDao.insertCheckResult(CheckResultEntity.fromDomain(result))
    override suspend fun getLastCheckResult(resourceId: Long): CheckResult? = checkResultDao.getLastCheckResult(resourceId)?.toDomain()
    override fun getLastCheckResults(): Flow<List<CheckResult>> = checkResultDao.getLastCheckResults().map { it.map { e -> e.toDomain() } }
    override suspend fun getLastCheckResultsOnce(): List<CheckResult> = checkResultDao.getLastCheckResultsOnce().map { it.toDomain() }
    override suspend fun getCheckHistory(resourceId: Long, limit: Int): List<CheckResult> = checkResultDao.getCheckHistory(resourceId, limit).map { it.toDomain() }
    override suspend fun deleteOldCheckResults(olderThanMs: Long): Int = checkResultDao.deleteOldCheckResults(System.currentTimeMillis() - olderThanMs)
    override suspend fun deleteAllCheckResults() = checkResultDao.deleteAllCheckResults()
    override suspend fun getAverageResponseTime(resourceId: Long, periodMs: Long): Long = checkResultDao.getAverageResponseTime(resourceId, System.currentTimeMillis() - periodMs) ?: 0L
    override suspend fun isResourceAvailable(resource: Resource): Boolean = networkDiagnostics.isAvailable(resource)
}
''')

w(f"{JAVA}/data/repository/HistoryRepositoryImpl.kt", '''package com.netweather.data.repository

import com.netweather.data.local.db.dao.HistoryDao
import com.netweather.data.local.db.entity.HistoryEntity
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.domain.repository.HistoryRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class HistoryRepositoryImpl @Inject constructor(private val historyDao: HistoryDao) : HistoryRepository {
    override suspend fun saveHistoryEntry(entry: HistoryEntry): Long = historyDao.insertHistoryEntry(HistoryEntity.fromDomain(entry))
    override fun getHistory(period: HistoryPeriod): Flow<List<HistoryEntry>> = historyDao.getHistorySince(System.currentTimeMillis() - period.getDurationMs()).map { it.map { e -> e.toDomain() } }
    override suspend fun getHistoryOnce(period: HistoryPeriod): List<HistoryEntry> = historyDao.getHistorySinceOnce(System.currentTimeMillis() - period.getDurationMs()).map { it.toDomain() }
    override suspend fun getLastHistoryEntry(): HistoryEntry? = historyDao.getLastHistoryEntry()?.toDomain()
    override suspend fun deleteOldHistory(olderThanMs: Long): Int = historyDao.deleteOldHistory(System.currentTimeMillis() - olderThanMs)
    override suspend fun deleteAllHistory() = historyDao.deleteAllHistory()
    override suspend fun getHistoryCount(): Int = historyDao.getHistoryCount()
    override suspend fun getStatistics(period: HistoryPeriod): Map<String, Any> {
        val since = System.currentTimeMillis() - period.getDurationMs()
        return mapOf(
            "normalCount" to historyDao.getCountByNetworkMode("NORMAL", since),
            "partialCount" to historyDao.getCountByNetworkMode("PARTIAL_DEGRADATION", since),
            "restrictedCount" to historyDao.getCountByNetworkMode("RESTRICTED_ACCESS", since),
            "noInternetCount" to historyDao.getCountByNetworkMode("NO_INTERNET", since)
        )
    }
    override suspend fun getAverageAvailabilityIndex(period: HistoryPeriod): Int = historyDao.getAverageAvailabilityIndex(System.currentTimeMillis() - period.getDurationMs()) ?: 0
    override suspend fun getMinAvailabilityIndex(period: HistoryPeriod): Int = historyDao.getMinAvailabilityIndex(System.currentTimeMillis() - period.getDurationMs()) ?: 0
    override suspend fun getMaxAvailabilityIndex(period: HistoryPeriod): Int = historyDao.getMaxAvailabilityIndex(System.currentTimeMillis() - period.getDurationMs()) ?: 0
}
''')

w(f"{JAVA}/data/repository/SettingsRepositoryImpl.kt", '''package com.netweather.data.repository

import com.netweather.data.local.preferences.PreferencesManager
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import com.netweather.domain.repository.SettingsRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SettingsRepositoryImpl @Inject constructor(private val preferencesManager: PreferencesManager) : SettingsRepository {
    override fun getSettings(): Flow<Settings> = preferencesManager.getSettings()
    override suspend fun getSettingsOnce(): Settings = preferencesManager.getSettings().first()
    override suspend fun saveSettings(settings: Settings) = preferencesManager.saveSettings(settings)
    override suspend fun setThemeMode(themeMode: ThemeMode) = preferencesManager.setThemeMode(themeMode)
    override suspend fun setCheckInterval(minutes: Int) = preferencesManager.setCheckInterval(minutes)
    override suspend fun setNotificationsEnabled(enabled: Boolean) = preferencesManager.setNotificationsEnabled(enabled)
    override suspend fun setNotifyOnFailure(enabled: Boolean) = preferencesManager.setNotifyOnFailure(enabled)
    override suspend fun setNotifyOnRecovery(enabled: Boolean) = preferencesManager.setNotifyOnRecovery(enabled)
    override suspend fun setNotifyOnSlowResponse(enabled: Boolean) = preferencesManager.setNotifyOnSlowResponse(enabled)
    override suspend fun setHistoryRetentionDays(days: Int) = preferencesManager.setHistoryRetentionDays(days)
    override suspend fun resetToDefaults() = preferencesManager.resetToDefaults()
}
''')

print("✅ Data repositories created")

# DI
w(f"{JAVA}/di/AppModule.kt", '''package com.netweather.di

import android.content.Context
import com.netweather.data.local.preferences.PreferencesManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton
    fun providePreferencesManager(@ApplicationContext context: Context): PreferencesManager = PreferencesManager(context)
}
''')

w(f"{JAVA}/di/DatabaseModule.kt", '''package com.netweather.di

import android.content.Context
import androidx.room.Room
import com.netweather.data.local.db.AppDatabase
import com.netweather.data.local.db.dao.CheckResultDao
import com.netweather.data.local.db.dao.HistoryDao
import com.netweather.data.local.db.dao.ResourceDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides @Singleton
    fun provideAppDatabase(@ApplicationContext context: Context): AppDatabase = Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, "netweather_db").fallbackToDestructiveMigration().build()
    
    @Provides @Singleton fun provideResourceDao(db: AppDatabase): ResourceDao = db.resourceDao()
    @Provides @Singleton fun provideCheckResultDao(db: AppDatabase): CheckResultDao = db.checkResultDao()
    @Provides @Singleton fun provideHistoryDao(db: AppDatabase): HistoryDao = db.historyDao()
}
''')

w(f"{JAVA}/di/NetworkModule.kt", '''package com.netweather.di

import com.netweather.data.remote.NetworkClient
import com.netweather.data.remote.NetworkDiagnostics
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides @Singleton fun provideNetworkClient(): NetworkClient = NetworkClient()
    @Provides @Singleton fun provideNetworkDiagnostics(client: NetworkClient): NetworkDiagnostics = NetworkDiagnostics(client)
}
''')

w(f"{JAVA}/di/RepositoryModule.kt", '''package com.netweather.di

import com.netweather.data.repository.*
import com.netweather.domain.repository.*
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds @Singleton abstract fun bindResourceRepository(impl: ResourceRepositoryImpl): ResourceRepository
    @Binds @Singleton abstract fun bindDiagnosticsRepository(impl: DiagnosticsRepositoryImpl): DiagnosticsRepository
    @Binds @Singleton abstract fun bindHistoryRepository(impl: HistoryRepositoryImpl): HistoryRepository
    @Binds @Singleton abstract fun bindSettingsRepository(impl: SettingsRepositoryImpl): SettingsRepository
}
''')

print("✅ DI created")

print("\n✅✅✅ FIRST PART DONE ✅✅✅")
print("Script will continue in next message...")

# ============================================
# PRESENTATION - THEME
# ============================================
w(f"{JAVA}/presentation/theme/Color.kt", '''package com.netweather.presentation.theme

import androidx.compose.ui.graphics.Color

object NetWeatherColors {
    val md_theme_light_primary = Color(0xFF006C4C)
    val md_theme_light_onPrimary = Color(0xFFFFFFFF)
    val md_theme_light_primaryContainer = Color(0xFF89F8C7)
    val md_theme_light_secondary = Color(0xFF4D6357)
    val md_theme_light_onSecondary = Color(0xFFFFFFFF)
    val md_theme_light_background = Color(0xFFFBFDF8)
    val md_theme_light_onBackground = Color(0xFF191C1A)
    val md_theme_light_surface = Color(0xFFFBFDF8)
    val md_theme_light_onSurface = Color(0xFF191C1A)
    val md_theme_light_surfaceVariant = Color(0xFFDBE5DD)
    val md_theme_light_onSurfaceVariant = Color(0xFF404943)
    val md_theme_light_error = Color(0xFFBA1A1A)
    val md_theme_light_onError = Color(0xFFFFFFFF)
    
    val md_theme_dark_primary = Color(0xFF6CDBAC)
    val md_theme_dark_onPrimary = Color(0xFF003826)
    val md_theme_dark_primaryContainer = Color(0xFF005138)
    val md_theme_dark_secondary = Color(0xFFB4CCBE)
    val md_theme_dark_onSecondary = Color(0xFF20352A)
    val md_theme_dark_background = Color(0xFF191C1A)
    val md_theme_dark_onBackground = Color(0xFFE1E3DE)
    val md_theme_dark_surface = Color(0xFF191C1A)
    val md_theme_dark_onSurface = Color(0xFFE1E3DE)
    val md_theme_dark_surfaceVariant = Color(0xFF404943)
    val md_theme_dark_onSurfaceVariant = Color(0xFFBFC9C2)
    val md_theme_dark_error = Color(0xFFFFB4AB)
    val md_theme_dark_onError = Color(0xFF690005)
    
    val statusNormal = Color(0xFF2ECC71)
    val statusWarning = Color(0xFFF1C40F)
    val statusRestricted = Color(0xFFE67E22)
    val statusError = Color(0xFFE74C3C)
    val statusUnknown = Color(0xFF95A5A6)
    val chartLine = Color(0xFF006C4C)
    val chartFill = Color(0x33006C4C)
    val chartGrid = Color(0xFFE0E0E0)
}
''')

w(f"{JAVA}/presentation/theme/Type.kt", '''package com.netweather.presentation.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val NetWeatherTypography = Typography(
    displayLarge = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.Bold, fontSize = 57.sp, lineHeight = 64.sp),
    headlineMedium = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.SemiBold, fontSize = 28.sp, lineHeight = 36.sp),
    titleMedium = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 24.sp),
    bodyLarge = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 16.sp),
    labelSmall = TextStyle(fontFamily = FontFamily.Default, fontWeight = FontWeight.Medium, fontSize = 11.sp, lineHeight = 16.sp)
)
''')

w(f"{JAVA}/presentation/theme/Theme.kt", '''package com.netweather.presentation.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.ThemeMode

private val LightColorScheme = lightColorScheme(
    primary = NetWeatherColors.md_theme_light_primary,
    onPrimary = NetWeatherColors.md_theme_light_onPrimary,
    primaryContainer = NetWeatherColors.md_theme_light_primaryContainer,
    secondary = NetWeatherColors.md_theme_light_secondary,
    onSecondary = NetWeatherColors.md_theme_light_onSecondary,
    background = NetWeatherColors.md_theme_light_background,
    onBackground = NetWeatherColors.md_theme_light_onBackground,
    surface = NetWeatherColors.md_theme_light_surface,
    onSurface = NetWeatherColors.md_theme_light_onSurface,
    surfaceVariant = NetWeatherColors.md_theme_light_surfaceVariant,
    onSurfaceVariant = NetWeatherColors.md_theme_light_onSurfaceVariant,
    error = NetWeatherColors.md_theme_light_error,
    onError = NetWeatherColors.md_theme_light_onError
)

private val DarkColorScheme = darkColorScheme(
    primary = NetWeatherColors.md_theme_dark_primary,
    onPrimary = NetWeatherColors.md_theme_dark_onPrimary,
    primaryContainer = NetWeatherColors.md_theme_dark_primaryContainer,
    secondary = NetWeatherColors.md_theme_dark_secondary,
    onSecondary = NetWeatherColors.md_theme_dark_onSecondary,
    background = NetWeatherColors.md_theme_dark_background,
    onBackground = NetWeatherColors.md_theme_dark_onBackground,
    surface = NetWeatherColors.md_theme_dark_surface,
    onSurface = NetWeatherColors.md_theme_dark_onSurface,
    surfaceVariant = NetWeatherColors.md_theme_dark_surfaceVariant,
    onSurfaceVariant = NetWeatherColors.md_theme_dark_onSurfaceVariant,
    error = NetWeatherColors.md_theme_dark_error,
    onError = NetWeatherColors.md_theme_dark_onError
)

@Composable
fun NetWeatherTheme(themeMode: ThemeMode = ThemeMode.SYSTEM, dynamicColor: Boolean = true, content: @Composable () -> Unit) {
    val darkTheme = when (themeMode) {
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
    }
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.surface.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }
    MaterialTheme(colorScheme = colorScheme, typography = NetWeatherTypography, content = content)
}

@Composable
fun NetworkMode.getStatusColor(): androidx.compose.ui.graphics.Color = when (this) {
    NetworkMode.NORMAL -> NetWeatherColors.statusNormal
    NetworkMode.PARTIAL_DEGRADATION -> NetWeatherColors.statusWarning
    NetworkMode.RESTRICTED_ACCESS -> NetWeatherColors.statusRestricted
    NetworkMode.NO_INTERNET -> NetWeatherColors.statusError
}

@Composable
fun NetworkMode.getStatusBackgroundColor(): androidx.compose.ui.graphics.Color = when (this) {
    NetworkMode.NORMAL -> NetWeatherColors.statusNormal.copy(alpha = 0.2f)
    NetworkMode.PARTIAL_DEGRADATION -> NetWeatherColors.statusWarning.copy(alpha = 0.2f)
    NetworkMode.RESTRICTED_ACCESS -> NetWeatherColors.statusRestricted.copy(alpha = 0.2f)
    NetworkMode.NO_INTERNET -> NetWeatherColors.statusError.copy(alpha = 0.2f)
}

@Composable
fun com.netweather.domain.model.DiagnosticStatus.getStatusColor(): androidx.compose.ui.graphics.Color = when (this) {
    com.netweather.domain.model.DiagnosticStatus.OK -> NetWeatherColors.statusNormal
    com.netweather.domain.model.DiagnosticStatus.TIMEOUT -> NetWeatherColors.statusWarning
    com.netweather.domain.model.DiagnosticStatus.UNKNOWN_ERROR -> NetWeatherColors.statusUnknown
    else -> NetWeatherColors.statusError
}
''')

w(f"{JAVA}/presentation/theme/Shape.kt", '''package com.netweather.presentation.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

val NetWeatherShapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(16.dp),
    extraLarge = RoundedCornerShape(24.dp)
)
''')

print("✅ Theme created")

# ============================================
# PRESENTATION - NAVIGATION
# ============================================
w(f"{JAVA}/presentation/navigation/NavigationRoutes.kt", '''package com.netweather.presentation.navigation

object NavigationRoutes {
    const val MAIN = "main"
    const val HISTORY = "history"
    const val SETTINGS = "settings"
}
''')

w(f"{JAVA}/presentation/navigation/Navigation.kt", '''package com.netweather.presentation.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.netweather.presentation.history.HistoryScreen
import com.netweather.presentation.main.MainScreen
import com.netweather.presentation.settings.SettingsScreen

@Composable
fun NetWeatherNavigation() {
    val navController = rememberNavController()
    Scaffold(
        bottomBar = {
            val navBackStackEntry by navController.currentBackStackEntryAsState()
            val currentDestination = navBackStackEntry?.destination
            NavigationBar {
                navigationItems.forEach { item ->
                    NavigationBarItem(
                        icon = { Icon(imageVector = item.icon, contentDescription = item.label) },
                        label = { Text(item.label) },
                        selected = currentDestination?.hierarchy?.any { it.route == item.route } == true,
                        onClick = {
                            navController.navigate(item.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = NavigationRoutes.MAIN,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(NavigationRoutes.MAIN) { MainScreen() }
            composable(NavigationRoutes.HISTORY) { HistoryScreen() }
            composable(NavigationRoutes.SETTINGS) { SettingsScreen() }
        }
    }
}

data class NavigationItem(val route: String, val icon: ImageVector, val label: String)

private val navigationItems = listOf(
    NavigationItem(NavigationRoutes.MAIN, Icons.Default.Home, "Main"),
    NavigationItem(NavigationRoutes.HISTORY, Icons.Default.History, "History"),
    NavigationItem(NavigationRoutes.SETTINGS, Icons.Default.Settings, "Settings")
)
''')

print("✅ Navigation created")

# ============================================
# PRESENTATION - MAIN
# ============================================
w(f"{JAVA}/presentation/main/MainViewModel.kt", '''package com.netweather.presentation.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.netweather.domain.model.*
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.usecase.CalculateAvailabilityIndexUseCase
import com.netweather.domain.usecase.CheckAllResourcesUseCase
import com.netweather.domain.usecase.DetermineNetworkModeUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val checkAllResourcesUseCase: CheckAllResourcesUseCase,
    private val calculateAvailabilityIndexUseCase: CalculateAvailabilityIndexUseCase,
    private val determineNetworkModeUseCase: DetermineNetworkModeUseCase
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(MainUiState())
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()
    
    init { observeResources(); refreshData() }
    
    private fun observeResources() {
        viewModelScope.launch {
            resourceRepository.getAllResources().collect { resources ->
                updateResourceStates(resources)
            }
        }
    }
    
    fun refreshData() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val checkResult = checkAllResourcesUseCase.checkAllOnce()
                if (checkResult.isFailure) {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = checkResult.exceptionOrNull()?.message ?: "Error")
                    return@launch
                }
                val checkResults = checkResult.getOrDefault(emptyList())
                val resources = resourceRepository.getAllResourcesOnce()
                val indexResult = calculateAvailabilityIndexUseCase(resources, checkResults)
                val availabilityIndex = indexResult.getOrNull() ?: AvailabilityIndex.create(0)
                val modeResult = determineNetworkModeUseCase(availabilityIndex, resources, checkResults)
                val networkMode = modeResult.getOrNull() ?: NetworkMode.NO_INTERNET
                val availableCount = checkResults.count { it.isSuccessful() }
                val unavailableCount = checkResults.size - availableCount
                val resourceStates = createResourceStates(resources, checkResults)
                _uiState.value = MainUiState(
                    isLoading = false,
                    networkState = NetworkState(
                        availabilityIndex = availabilityIndex,
                        networkMode = networkMode,
                        lastCheckTime = System.currentTimeMillis(),
                        availableCount = availableCount,
                        unavailableCount = unavailableCount,
                        totalResources = resources.size,
                        resourceStates = resourceStates
                    )
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message ?: "Unknown error")
            }
        }
    }
    
    private suspend fun updateResourceStates(resources: List<Resource>) {
        val checkResults = diagnosticsRepository.getLastCheckResultsOnce()
        val resourceStates = createResourceStates(resources, checkResults)
        val currentState = _uiState.value.networkState
        if (currentState != null) {
            _uiState.value = _uiState.value.copy(networkState = currentState.copy(resourceStates = resourceStates))
        }
    }
    
    private fun createResourceStates(resources: List<Resource>, checkResults: List<CheckResult>): Map<ResourceGroup, List<ResourceState>> {
        val resultsMap = checkResults.associateBy { it.resourceId }
        return resources.groupBy { it.group }.mapValues { (_, groupResources) ->
            groupResources.map { resource ->
                val checkResult = resultsMap[resource.id]
                ResourceState(
                    resource = resource,
                    lastCheckResult = checkResult,
                    isAvailable = checkResult?.isSuccessful() == true,
                    responseTimeMs = checkResult?.responseTimeMs ?: 0,
                    lastCheckTime = checkResult?.timestamp ?: 0
                )
            }.sortedBy { it.resource.name }
        }
    }
    
    fun toggleResource(resourceId: Long) {
        viewModelScope.launch {
            val resource = resourceRepository.getResourceById(resourceId) ?: return@launch
            resourceRepository.setResourceEnabled(resourceId, !resource.enabled)
        }
    }
    
    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
}

data class MainUiState(
    val isLoading: Boolean = false,
    val networkState: NetworkState? = null,
    val error: String? = null
) {
    fun hasData(): Boolean = networkState != null
    fun hasError(): Boolean = error != null
}
''')

w(f"{JAVA}/presentation/main/MainScreen.kt", '''package com.netweather.presentation.main

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.netweather.domain.model.ResourceGroup
import com.netweather.presentation.main.components.AvailabilityIndexCard
import com.netweather.presentation.main.components.NetworkModeCard
import com.netweather.presentation.main.components.ResourceGroupSection

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.error) {
        uiState.error?.let { error ->
            snackbarHostState.showSnackbar(message = error, actionLabel = "OK")
            viewModel.clearError()
        }
    }
    Scaffold(
        topBar = { TopAppBar(title = { Text("NetWeather", style = MaterialTheme.typography.headlineMedium) }, colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)) },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        PullToRefreshBox(
            isRefreshing = uiState.isLoading,
            onRefresh = { viewModel.refreshData() },
            modifier = Modifier.fillMaxSize().padding(paddingValues)
        ) {
            if (uiState.hasData()) {
                MainContent(uiState = uiState, onToggleResource = { viewModel.toggleResource(it) })
            } else if (!uiState.isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("🌐", style = MaterialTheme.typography.displayLarge)
                        Spacer(Modifier.height(16.dp))
                        Text("No data", style = MaterialTheme.typography.headlineSmall)
                        Text("Pull down to refresh", style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
                    }
                }
            }
        }
    }
}

@Composable
private fun MainContent(uiState: MainUiState, onToggleResource: (Long) -> Unit) {
    val networkState = uiState.networkState ?: return
    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { AvailabilityIndexCard(availabilityIndex = networkState.availabilityIndex, lastCheckTime = networkState.lastCheckTime) }
        item { NetworkModeCard(networkMode = networkState.networkMode, availableCount = networkState.availableCount, unavailableCount = networkState.unavailableCount, totalResources = networkState.totalResources) }
        networkState.resourceStates[ResourceGroup.RU]?.let { resources ->
            if (resources.isNotEmpty()) item { ResourceGroupSection(group = ResourceGroup.RU, resources = resources, onToggleResource = onToggleResource) }
        }
        networkState.resourceStates[ResourceGroup.INTL]?.let { resources ->
            if (resources.isNotEmpty()) item { ResourceGroupSection(group = ResourceGroup.INTL, resources = resources, onToggleResource = onToggleResource) }
        }
        networkState.resourceStates[ResourceGroup.CUSTOM]?.let { resources ->
            if (resources.isNotEmpty()) item { ResourceGroupSection(group = ResourceGroup.CUSTOM, resources = resources, onToggleResource = onToggleResource) }
        }
    }
}
''')

w(f"{JAVA}/presentation/main/components/AvailabilityIndexCard.kt", '''package com.netweather.presentation.main.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.AvailabilityIndex
import com.netweather.presentation.theme.NetWeatherColors
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun AvailabilityIndexCard(availabilityIndex: AvailabilityIndex, lastCheckTime: Long, modifier: Modifier = Modifier) {
    val animatedProgress by animateFloatAsState(targetValue = availabilityIndex.value / 100f, animationSpec = tween(durationMillis = 1000), label = "Progress")
    val statusColor = when {
        availabilityIndex.value >= 80 -> NetWeatherColors.statusNormal
        availabilityIndex.value >= 70 -> NetWeatherColors.statusWarning
        availabilityIndex.value >= 30 -> NetWeatherColors.statusRestricted
        else -> NetWeatherColors.statusError
    }
    Card(modifier = modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Availability Index", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(16.dp))
            Box(contentAlignment = Alignment.Center, modifier = Modifier.size(160.dp)) {
                Canvas(modifier = Modifier.size(160.dp)) {
                    val strokeWidth = 12.dp.toPx()
                    val radius = (size.minDimension - strokeWidth) / 2
                    val topLeft = Offset((size.width - radius * 2) / 2, (size.height - radius * 2) / 2)
                    val arcSize = Size(radius * 2, radius * 2)
                    drawArc(color = MaterialTheme.colorScheme.surfaceVariant, startAngle = -90f, sweepAngle = 360f, useCenter = false, topLeft = topLeft, size = arcSize, style = Stroke(width = strokeWidth, cap = StrokeCap.Round))
                    drawArc(color = statusColor, startAngle = -90f, sweepAngle = 360f * animatedProgress, useCenter = false, topLeft = topLeft, size = arcSize, style = Stroke(width = strokeWidth, cap = StrokeCap.Round))
                }
                Text("${availabilityIndex.value}%", style = MaterialTheme.typography.displayLarge, fontWeight = FontWeight.Bold, color = statusColor)
            }
            Spacer(Modifier.height(16.dp))
            val statusText = when { availabilityIndex.value >= 80 -> "Excellent"; availabilityIndex.value >= 70 -> "Good"; availabilityIndex.value >= 30 -> "Acceptable"; else -> "Poor" }
            Text(statusText, style = MaterialTheme.typography.titleLarge, color = statusColor, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(8.dp))
            val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
            Text("Updated at ${timeFormat.format(Date(lastCheckTime))}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
''')

w(f"{JAVA}/presentation/main/components/NetworkModeCard.kt", '''package com.netweather.presentation.main.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.NetworkMode
import com.netweather.presentation.theme.getStatusBackgroundColor
import com.netweather.presentation.theme.getStatusColor

@Composable
fun NetworkModeCard(networkMode: NetworkMode, availableCount: Int, unavailableCount: Int, totalResources: Int, modifier: Modifier = Modifier) {
    val statusColor = networkMode.getStatusColor()
    val backgroundColor = networkMode.getStatusBackgroundColor()
    Card(modifier = modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = backgroundColor), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(networkMode.getEmoji(), style = MaterialTheme.typography.displaySmall)
                Text(networkMode.getTitle(), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = statusColor)
            }
            Spacer(Modifier.height(12.dp))
            Text(networkMode.getDescription(), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
            Spacer(Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                StatItem("Available", "$availableCount", statusColor)
                StatItem("Unavailable", "$unavailableCount", if (unavailableCount > 0) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
                StatItem("Total", "$totalResources", MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String, color: androidx.compose.ui.graphics.Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = color)
        Spacer(Modifier.height(4.dp))
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
''')

w(f"{JAVA}/presentation/main/components/ResourceGroupSection.kt", '''package com.netweather.presentation.main.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.ResourceState

@Composable
fun ResourceGroupSection(group: ResourceGroup, resources: List<ResourceState>, onToggleResource: (Long) -> Unit, modifier: Modifier = Modifier) {
    val groupTitle = when (group) {
        ResourceGroup.RU -> "🇷🇺 Russian resources"
        ResourceGroup.INTL -> "🌍 International resources"
        ResourceGroup.CUSTOM -> "⭐ Custom resources"
    }
    val availableCount = resources.count { it.isAvailable }
    Card(modifier = modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text(groupTitle, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(4.dp))
            Text("Available: $availableCount of ${resources.size}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                resources.forEach { resourceState ->
                    ResourceItem(resourceState = resourceState, onToggle = { onToggleResource(resourceState.resource.id) })
                }
            }
        }
    }
}
''')

w(f"{JAVA}/presentation/main/components/ResourceItem.kt", '''package com.netweather.presentation.main.components

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.ResourceState
import com.netweather.presentation.theme.getStatusColor

@Composable
fun ResourceItem(resourceState: ResourceState, onToggle: () -> Unit, modifier: Modifier = Modifier) {
    val statusColor = resourceState.getDiagnosticStatus().getStatusColor()
    Surface(modifier = modifier.fillMaxWidth(), color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f), shape = MaterialTheme.shapes.small) {
        Row(modifier = Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                Surface(modifier = Modifier.size(12.dp), shape = MaterialTheme.shapes.extraSmall, color = statusColor) {}
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(resourceState.resource.name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (resourceState.isAvailable) {
                        Text("${resourceState.responseTimeMs} ms", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        Text(resourceState.getErrorDescription(), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
            IconButton(onClick = onToggle, modifier = Modifier.size(40.dp)) {
                Icon(
                    imageVector = if (resourceState.resource.enabled) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                    contentDescription = "Toggle",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
''')

print("✅ Main screen created")

# ============================================
# PRESENTATION - HISTORY
# ============================================
w(f"{JAVA}/presentation/history/HistoryViewModel.kt", '''package com.netweather.presentation.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.domain.repository.HistoryRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class HistoryViewModel @Inject constructor(private val historyRepository: HistoryRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(HistoryUiState())
    val uiState: StateFlow<HistoryUiState> = _uiState.asStateFlow()
    private val _selectedPeriod = MutableStateFlow(HistoryPeriod.DAY)
    val selectedPeriod: StateFlow<HistoryPeriod> = _selectedPeriod.asStateFlow()
    init { loadHistory() }
    fun loadHistory() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val period = _selectedPeriod.value
                val history = historyRepository.getHistoryOnce(period)
                val statistics = historyRepository.getStatistics(period)
                val averageIndex = historyRepository.getAverageAvailabilityIndex(period)
                val minIndex = historyRepository.getMinAvailabilityIndex(period)
                val maxIndex = historyRepository.getMaxAvailabilityIndex(period)
                _uiState.value = HistoryUiState(
                    historyEntries = history,
                    statistics = HistoryStatistics(
                        averageIndex = averageIndex, minIndex = minIndex, maxIndex = maxIndex,
                        totalEntries = history.size,
                        normalCount = statistics["normalCount"] as? Int ?: 0,
                        partialCount = statistics["partialCount"] as? Int ?: 0,
                        restrictedCount = statistics["restrictedCount"] as? Int ?: 0,
                        noInternetCount = statistics["noInternetCount"] as? Int ?: 0
                    )
                )
            } catch (e: Exception) { _uiState.value = _uiState.value.copy(error = e.message) }
        }
    }
    fun selectPeriod(period: HistoryPeriod) { _selectedPeriod.value = period; loadHistory() }
    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
}

data class HistoryUiState(val isLoading: Boolean = false, val historyEntries: List<HistoryEntry> = emptyList(), val statistics: HistoryStatistics? = null, val error: String? = null) {
    fun hasData(): Boolean = historyEntries.isNotEmpty()
}

data class HistoryStatistics(val averageIndex: Int, val minIndex: Int, val maxIndex: Int, val totalEntries: Int, val normalCount: Int, val partialCount: Int, val restrictedCount: Int, val noInternetCount: Int) {
    fun getModePercentages(): Map<String, Int> {
        if (totalEntries == 0) return mapOf("normal" to 0, "partial" to 0, "restricted" to 0, "noInternet" to 0)
        return mapOf("normal" to (normalCount * 100) / totalEntries, "partial" to (partialCount * 100) / totalEntries, "restricted" to (restrictedCount * 100) / totalEntries, "noInternet" to (noInternetCount * 100) / totalEntries)
    }
}
''')

w(f"{JAVA}/presentation/history/HistoryScreen.kt", '''package com.netweather.presentation.history

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.netweather.domain.model.HistoryPeriod
import com.netweather.presentation.history.components.HistoryChart
import com.netweather.presentation.history.components.HistoryItem
import com.netweather.presentation.history.components.StatisticsCard

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(viewModel: HistoryViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val selectedPeriod by viewModel.selectedPeriod.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.error) { uiState.error?.let { snackbarHostState.showSnackbar(it); viewModel.clearError() } }
    Scaffold(
        topBar = { TopAppBar(title = { Text("History", style = MaterialTheme.typography.headlineMedium) }, colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)) },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        if (uiState.hasData()) {
            LazyColumn(modifier = Modifier.fillMaxSize().padding(paddingValues), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                item {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        HistoryPeriod.values().forEach { period ->
                            FilterChip(selected = selectedPeriod == period, onClick = { viewModel.selectPeriod(period) }, label = { Text(period.getTitle()) }, modifier = Modifier.weight(1f))
                        }
                    }
                }
                item { HistoryChart(historyEntries = uiState.historyEntries, period = selectedPeriod) }
                uiState.statistics?.let { item { StatisticsCard(statistics = it) } }
                items(uiState.historyEntries) { entry -> HistoryItem(entry = entry) }
            }
        } else {
            Box(modifier = Modifier.fillMaxSize().padding(paddingValues), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("📊", style = MaterialTheme.typography.displayLarge)
                    Spacer(Modifier.height(16.dp))
                    Text("History is empty", style = MaterialTheme.typography.headlineSmall)
                    Text("Data will appear after first checks", style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
                }
            }
        }
    }
}
''')

w(f"{JAVA}/presentation/history/components/HistoryChart.kt", '''package com.netweather.presentation.history.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.presentation.theme.NetWeatherColors

@Composable
fun HistoryChart(historyEntries: List<HistoryEntry>, period: HistoryPeriod, modifier: Modifier = Modifier) {
    Card(modifier = modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text("Availability Chart", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            Canvas(modifier = Modifier.fillMaxWidth().height(200.dp)) {
                if (historyEntries.isEmpty()) return@Canvas
                val sorted = historyEntries.sortedBy { it.timestamp }
                val width = size.width; val height = size.height; val padding = 40.dp.toPx()
                val chartWidth = width - padding * 2; val chartHeight = height - padding * 2
                for (i in 0..4) { val y = padding + (chartHeight / 4) * i; drawLine(color = NetWeatherColors.chartGrid, start = Offset(padding, y), end = Offset(width - padding, y), strokeWidth = 1.dp.toPx()) }
                val path = Path(); val fillPath = Path()
                sorted.forEachIndexed { index, entry ->
                    val x = padding + (chartWidth * index) / (sorted.size - 1).coerceAtLeast(1)
                    val y = padding + chartHeight - (chartHeight * entry.availabilityIndex / 100f)
                    if (index == 0) { path.moveTo(x, y); fillPath.moveTo(x, padding + chartHeight); fillPath.lineTo(x, y) } else { path.lineTo(x, y); fillPath.lineTo(x, y) }
                    if (index == sorted.size - 1) { fillPath.lineTo(x, padding + chartHeight); fillPath.close() }
                }
                drawPath(path = fillPath, color = NetWeatherColors.chartFill)
                drawPath(path = path, color = NetWeatherColors.chartLine, style = Stroke(width = 2.dp.toPx()))
                sorted.forEachIndexed { index, entry ->
                    val x = padding + (chartWidth * index) / (sorted.size - 1).coerceAtLeast(1)
                    val y = padding + chartHeight - (chartHeight * entry.availabilityIndex / 100f)
                    val color = when { entry.availabilityIndex >= 80 -> NetWeatherColors.statusNormal; entry.availabilityIndex >= 70 -> NetWeatherColors.statusWarning; entry.availabilityIndex >= 30 -> NetWeatherColors.statusRestricted; else -> NetWeatherColors.statusError }
                    drawCircle(color = color, radius = 4.dp.toPx(), center = Offset(x, y))
                }
            }
        }
    }
}
''')

w(f"{JAVA}/presentation/history/components/StatisticsCard.kt", '''package com.netweather.presentation.history.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.presentation.history.HistoryStatistics
import com.netweather.presentation.theme.NetWeatherColors

@Composable
fun StatisticsCard(statistics: HistoryStatistics, modifier: Modifier = Modifier) {
    Card(modifier = modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text("Statistics", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                StatValue("Average", "${statistics.averageIndex}%", getColorForIndex(statistics.averageIndex))
                StatValue("Min", "${statistics.minIndex}%", getColorForIndex(statistics.minIndex))
                StatValue("Max", "${statistics.maxIndex}%", getColorForIndex(statistics.maxIndex))
            }
            Spacer(Modifier.height(16.dp))
            val p = statistics.getModePercentages()
            ModeDist("Normal", p["normal"] ?: 0, NetWeatherColors.statusNormal)
            ModeDist("Partial degradation", p["partial"] ?: 0, NetWeatherColors.statusWarning)
            ModeDist("Restricted access", p["restricted"] ?: 0, NetWeatherColors.statusRestricted)
            ModeDist("No internet", p["noInternet"] ?: 0, NetWeatherColors.statusError)
        }
    }
}

@Composable
private fun StatValue(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = color)
        Spacer(Modifier.height(4.dp))
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ModeDist(label: String, percentage: Int, color: Color) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall)
        Text("$percentage%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold, color = color)
    }
}

private fun getColorForIndex(index: Int): Color = when {
    index >= 80 -> NetWeatherColors.statusNormal; index >= 70 -> NetWeatherColors.statusWarning; index >= 30 -> NetWeatherColors.statusRestricted; else -> NetWeatherColors.statusError
}
''')

w(f"{JAVA}/presentation/history/components/HistoryItem.kt", '''package com.netweather.presentation.history.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.HistoryEntry
import com.netweather.presentation.theme.getStatusColor
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun HistoryItem(entry: HistoryEntry, modifier: Modifier = Modifier) {
    val dateFormat = SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.getDefault())
    val statusColor = entry.networkMode.getStatusColor()
    Surface(modifier = modifier.fillMaxWidth(), color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f), shape = MaterialTheme.shapes.small) {
        Row(modifier = Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(modifier = Modifier.size(12.dp), shape = MaterialTheme.shapes.extraSmall, color = statusColor) {}
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(dateFormat.format(Date(entry.timestamp)), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(entry.networkMode.getEmoji(), style = MaterialTheme.typography.bodyMedium)
                    Text(entry.networkMode.getShortDescription(), style = MaterialTheme.typography.bodySmall, color = statusColor, fontWeight = FontWeight.SemiBold)
                }
                Spacer(Modifier.height(4.dp))
                Text("Available: ${entry.availableCount} | Unavailable: ${entry.unavailableCount}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("${entry.availabilityIndex}%", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = statusColor)
                Text("index", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
''')

print("✅ History screen created")

# ============================================
# PRESENTATION - SETTINGS
# ============================================
w(f"{JAVA}/presentation/settings/SettingsViewModel.kt", '''package com.netweather.presentation.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.Settings
import com.netweather.domain.model.ThemeMode
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import com.netweather.domain.usecase.AddResourceUseCase
import com.netweather.domain.usecase.DeleteResourceUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val settingsRepository: SettingsRepository,
    private val resourceRepository: ResourceRepository,
    private val addResourceUseCase: AddResourceUseCase,
    private val deleteResourceUseCase: DeleteResourceUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()
    init {
        viewModelScope.launch { settingsRepository.getSettings().collect { _uiState.value = _uiState.value.copy(settings = it) } }
        viewModelScope.launch { resourceRepository.getAllResources().collect { resources ->
            _uiState.value = _uiState.value.copy(
                resources = resources,
                russianResources = resources.filter { it.group == ResourceGroup.RU },
                internationalResources = resources.filter { it.group == ResourceGroup.INTL },
                customResources = resources.filter { it.group == ResourceGroup.CUSTOM }
            )
        }}
    }
    fun setThemeMode(m: ThemeMode) = viewModelScope.launch { settingsRepository.setThemeMode(m) }
    fun setCheckInterval(m: Int) = viewModelScope.launch { settingsRepository.setCheckInterval(m) }
    fun setNotificationsEnabled(e: Boolean) = viewModelScope.launch { settingsRepository.setNotificationsEnabled(e) }
    fun setNotifyOnFailure(e: Boolean) = viewModelScope.launch { settingsRepository.setNotifyOnFailure(e) }
    fun setNotifyOnRecovery(e: Boolean) = viewModelScope.launch { settingsRepository.setNotifyOnRecovery(e) }
    fun setNotifyOnSlowResponse(e: Boolean) = viewModelScope.launch { settingsRepository.setNotifyOnSlowResponse(e) }
    fun toggleResource(id: Long) = viewModelScope.launch { val r = resourceRepository.getResourceById(id) ?: return@launch; resourceRepository.setResourceEnabled(id, !r.enabled) }
    fun deleteResource(id: Long) = viewModelScope.launch { deleteResourceUseCase(id) }
    fun addCustomResource(name: String, url: String) = viewModelScope.launch { addResourceUseCase(name, url, ResourceGroup.CUSTOM) }
    fun resetSettings() = viewModelScope.launch { settingsRepository.resetToDefaults() }
    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
    fun clearSuccessMessage() { _uiState.value = _uiState.value.copy(successMessage = null) }
}

data class SettingsUiState(val settings: Settings = Settings(), val resources: List<Resource> = emptyList(), val russianResources: List<Resource> = emptyList(), val internationalResources: List<Resource> = emptyList(), val customResources: List<Resource> = emptyList(), val error: String? = null, val successMessage: String? = null)
''')

w(f"{JAVA}/presentation/settings/SettingsScreen.kt", '''package com.netweather.presentation.settings

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.netweather.presentation.settings.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: SettingsViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(uiState.error) { uiState.error?.let { snackbarHostState.showSnackbar(it); viewModel.clearError() } }
    LaunchedEffect(uiState.successMessage) { uiState.successMessage?.let { snackbarHostState.showSnackbar(it); viewModel.clearSuccessMessage() } }
    Scaffold(
        topBar = { TopAppBar(title = { Text("Settings", style = MaterialTheme.typography.headlineMedium) }, colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)) },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            item { Text("Appearance", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { ThemeSelector(uiState.settings.themeMode) { viewModel.setThemeMode(it) } }
            item { Text("Check interval", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { IntervalSelector(uiState.settings.checkIntervalMinutes) { viewModel.setCheckInterval(it) } }
            item { Text("Notifications", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { NotificationsSettings(uiState.settings, viewModel::setNotificationsEnabled, viewModel::setNotifyOnFailure, viewModel::setNotifyOnRecovery, viewModel::setNotifyOnSlowResponse) }
            item { Text("Resources", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { ResourceGroupManager(uiState.russianResources, uiState.internationalResources, uiState.customResources, viewModel::toggleResource, viewModel::deleteResource, viewModel::addCustomResource) }
            item { Spacer(Modifier.height(16.dp)); OutlinedButton(onClick = { viewModel.resetSettings() }, modifier = Modifier.fillMaxWidth()) { Text("Reset settings") } }
        }
    }
}
''')

w(f"{JAVA}/presentation/settings/components/ThemeSelector.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.ThemeMode

@Composable
fun ThemeSelector(currentTheme: ThemeMode, onThemeSelected: (ThemeMode) -> Unit, modifier: Modifier = Modifier) {
    SettingsCard("Theme", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            ThemeMode.values().forEach { mode ->
                Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = currentTheme == mode, onClick = { onThemeSelected(mode) })
                    Spacer(Modifier.width(12.dp))
                    Text(mode.getTitle(), style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}
''')

w(f"{JAVA}/presentation/settings/components/IntervalSelector.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun IntervalSelector(currentInterval: Int, onIntervalSelected: (Int) -> Unit, modifier: Modifier = Modifier) {
    SettingsCard("Check interval", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Every $currentInterval minutes", style = MaterialTheme.typography.bodyLarge)
            Slider(value = currentInterval.toFloat(), onValueChange = { onIntervalSelected(it.toInt()) }, valueRange = 5f..60f, steps = 10)
            Text("From 5 to 60 minutes", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
''')

w(f"{JAVA}/presentation/settings/components/NotificationsSettings.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.Settings

@Composable
fun NotificationsSettings(settings: Settings, onMain: (Boolean) -> Unit, onFailure: (Boolean) -> Unit, onRecovery: (Boolean) -> Unit, onSlow: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    SettingsCard("Notifications", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Toggle("Enable notifications", "Get notifications about network state", settings.enableNotifications, onMain)
            if (settings.enableNotifications) {
                Toggle("Notify on failures", "When resource becomes unavailable", settings.notifyOnFailure, onFailure)
                Toggle("Notify on recovery", "When resource becomes available again", settings.notifyOnRecovery, onRecovery)
                Toggle("Notify on slow response", "When response time exceeds threshold", settings.notifyOnSlowResponse, onSlow)
            }
        }
    }
}

@Composable
private fun Toggle(title: String, desc: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(desc, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Switch(checked = checked, onCheckedChange = onChange)
    }
}
''')

w(f"{JAVA}/presentation/settings/components/ResourceGroupManager.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup

@Composable
fun ResourceGroupManager(ru: List<Resource>, intl: List<Resource>, custom: List<Resource>, onToggle: (Long) -> Unit, onDelete: (Long) -> Unit, onAdd: (String, String) -> Unit, modifier: Modifier = Modifier) {
    var showDialog by remember { mutableStateOf(false) }
    SettingsCard("Resources", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            GroupSection("🇷🇺 Russian", ru, onToggle)
            GroupSection("🌍 International", intl, onToggle)
            GroupSection("⭐ Custom", custom, onToggle, onDelete)
            Button(onClick = { showDialog = true }, modifier = Modifier.fillMaxWidth()) { Text("Add resource") }
        }
    }
    if (showDialog) AddResourceDialog(onDismiss = { showDialog = false }, onConfirm = { n, u -> onAdd(n, u); showDialog = false })
}

@Composable
private fun GroupSection(title: String, resources: List<Resource>, onToggle: (Long) -> Unit, onDelete: ((Long) -> Unit)? = null) {
    Column {
        Text(title, style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(8.dp))
        resources.forEach { r ->
            Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(r.name, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(r.url, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Switch(checked = r.enabled, onCheckedChange = { onToggle(r.id) })
                if (onDelete != null && r.group == ResourceGroup.CUSTOM) { TextButton(onClick = { onDelete(r.id) }) { Text("Delete", color = MaterialTheme.colorScheme.error) } }
            }
        }
    }
}
''')

w(f"{JAVA}/presentation/settings/components/AddResourceDialog.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun AddResourceDialog(onDismiss: () -> Unit, onConfirm: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }
    AlertDialog(onDismissRequest = onDismiss, title = { Text("Add resource") }, text = {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedTextField(value = url, onValueChange = { url = it }, label = { Text("URL") }, placeholder = { Text("https://example.com") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        }
    }, confirmButton = { TextButton(onClick = { if (name.isNotBlank() && url.isNotBlank()) onConfirm(name.trim(), url.trim()) }) { Text("Add") } }, dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } })
}
''')

w(f"{JAVA}/presentation/settings/components/SettingsCard.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun SettingsCard(title: String, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Card(modifier = modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(12.dp))
            content()
        }
    }
}
''')

print("✅ Settings screen created")

# ============================================
# APP + MAINACTIVITY
# ============================================
w(f"{JAVA}/NetWeatherApp.kt", '''package com.netweather

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.netweather.domain.repository.ResourceRepository
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltAndroidApp
class NetWeatherApp : Application(), Configuration.Provider {
    @Inject lateinit var workerFactory: HiltWorkerFactory
    @Inject lateinit var resourceRepository: ResourceRepository
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    override fun onCreate() {
        super.onCreate()
        applicationScope.launch { try { resourceRepository.initializeDefaultResources() } catch (e: Exception) { e.printStackTrace() } }
    }
    override val workManagerConfiguration: Configuration get() = Configuration.Builder().setWorkerFactory(workerFactory).build()
}
''')

w(f"{JAVA}/MainActivity.kt", '''package com.netweather

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.netweather.presentation.navigation.NetWeatherNavigation
import com.netweather.presentation.settings.SettingsViewModel
import com.netweather.presentation.theme.NetWeatherTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val notificationPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
        if (!isGranted) android.util.Log.d("MainActivity", "Notification permission denied")
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        requestNotificationPermission()
        setContent {
            val settingsViewModel: SettingsViewModel = hiltViewModel()
            val uiState by settingsViewModel.uiState.collectAsState()
            NetWeatherTheme(themeMode = uiState.settings.themeMode) {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) { NetWeatherNavigation() }
            }
        }
    }
    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED -> {}
                else -> notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
}
''')

print("✅ App + MainActivity created")

# ============================================
# WORKERS
# ============================================
w(f"{JAVA}/worker/WorkerScheduler.kt", '''package com.netweather.worker

import android.content.Context
import com.netweather.domain.repository.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

object WorkerScheduler {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    fun initialize(context: Context, settingsRepository: SettingsRepository) {
        scope.launch {
            try {
                val settings = settingsRepository.getSettingsOnce()
                PeriodicCheckWorker.enqueuePeriodicCheck(context, settings.checkIntervalMinutes.toLong())
                CleanupWorker.enqueuePeriodicCleanup(context)
            } catch (e: Exception) { e.printStackTrace() }
        }
    }
}
''')

w(f"{JAVA}/worker/PeriodicCheckWorker.kt", '''package com.netweather.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.netweather.domain.repository.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class PeriodicCheckWorker @AssistedInject constructor(
    @Assisted context: Context, @Assisted workerParams: WorkerParameters,
    private val resourceRepository: ResourceRepository, private val diagnosticsRepository: DiagnosticsRepository
) : CoroutineWorker(context, workerParams) {
    override suspend fun doWork(): Result {
        return try {
            val resources = resourceRepository.getAllResourcesOnce().filter { it.enabled }
            if (resources.isEmpty()) return Result.success()
            resources.forEach { resource ->
                try { val result = diagnosticsRepository.checkResource(resource); diagnosticsRepository.saveCheckResult(result) } catch (e: Exception) { e.printStackTrace() }
            }
            Result.success()
        } catch (e: Exception) { Result.retry() }
    }
    companion object {
        private const val WORK_NAME = "periodic_check_worker"
        fun enqueuePeriodicCheck(context: Context, intervalMinutes: Long = 15L) {
            val workRequest = PeriodicWorkRequestBuilder<PeriodicCheckWorker>(intervalMinutes, TimeUnit.MINUTES).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, workRequest)
        }
    }
}
''')

w(f"{JAVA}/worker/CleanupWorker.kt", '''package com.netweather.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.netweather.domain.repository.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class CleanupWorker @AssistedInject constructor(
    @Assisted context: Context, @Assisted workerParams: WorkerParameters,
    private val diagnosticsRepository: DiagnosticsRepository, private val historyRepository: HistoryRepository, private val settingsRepository: SettingsRepository
) : CoroutineWorker(context, workerParams) {
    override suspend fun doWork(): Result {
        return try {
            val settings = settingsRepository.getSettingsOnce()
            val retentionMs = settings.historyRetentionDays * 24L * 60L * 60L * 1000L
            diagnosticsRepository.deleteOldCheckResults(retentionMs)
            historyRepository.deleteOldHistory(retentionMs)
            Result.success()
        } catch (e: Exception) { Result.retry() }
    }
    companion object {
        fun enqueuePeriodicCleanup(context: Context) {
            val workRequest = PeriodicWorkRequestBuilder<CleanupWorker>(1, TimeUnit.DAYS).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork("cleanup_worker", ExistingPeriodicWorkPolicy.KEEP, workRequest)
        }
    }
}
''')

w(f"{JAVA}/worker/BootReceiver.kt", '''package com.netweather.worker

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.netweather.domain.repository.SettingsRepository
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class BootReceiver : BroadcastReceiver() {
    @Inject lateinit var settingsRepository: SettingsRepository
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            WorkerScheduler.initialize(context, settingsRepository)
        }
    }
}
''')

print("✅ Workers created")

# ============================================
# NOTIFICATIONS
# ============================================
w(f"{JAVA}/notification/NotificationManager.kt", '''package com.netweather.notification

import android.app.NotificationChannel
import android.app.NotificationManager as AndroidNotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.netweather.MainActivity
import com.netweather.R
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NotificationManager @Inject constructor(@ApplicationContext private val context: Context) {
    companion object { const val CHANNEL_ID_FAILURE = "resource_failure" }
    init { createChannels() }
    private fun createChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as AndroidNotificationManager
            manager.createNotificationChannel(NotificationChannel(CHANNEL_ID_FAILURE, "Resource failures", AndroidNotificationManager.IMPORTANCE_HIGH))
        }
    }
    fun notifyResourceFailure(resourceName: String, error: String) {
        val intent = Intent(context, MainActivity::class.java).apply { flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK }
        val pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_FAILURE).setSmallIcon(R.drawable.ic_notification).setContentTitle("Resource unavailable").setContentText("$resourceName: $error").setPriority(NotificationCompat.PRIORITY_HIGH).setContentIntent(pendingIntent).setAutoCancel(true).build()
        try { NotificationManagerCompat.from(context).notify(System.currentTimeMillis().toInt(), notification) } catch (e: SecurityException) { e.printStackTrace() }
    }
}
''')

w(f"{JAVA}/notification/NotificationActionReceiver.kt", '''package com.netweather.notification

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class NotificationActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {}
}
''')

print("✅ Notifications created")

# ============================================
# WIDGETS
# ============================================
w(f"{JAVA}/widget/WidgetUtils.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.content.ComponentName
import android.content.Context
import android.graphics.Color
import com.netweather.domain.model.NetworkState

object WidgetUtils {
    fun getIndexColor(index: Int): Int = when {
        index >= 80 -> Color.parseColor("#2ECC71")
        index >= 70 -> Color.parseColor("#F1C40F")
        index >= 30 -> Color.parseColor("#E67E22")
        else -> Color.parseColor("#E74C3C")
    }
    fun updateAllWidgets(context: Context, networkState: NetworkState?) {
        val mgr = AppWidgetManager.getInstance(context)
        listOf(SmallWidgetProvider::class.java, MediumWidgetProvider::class.java, LargeWidgetProvider::class.java).forEach { provider ->
            val ids = mgr.getAppWidgetIds(ComponentName(context, provider))
            ids.forEach { id ->
                val views = android.widget.RemoteViews(context.packageName, getLayoutForProvider(provider))
                if (networkState != null) {
                    views.setTextViewText(com.netweather.R.id.tv_availability_index, "${networkState.availabilityIndex.value}%")
                    views.setTextColor(com.netweather.R.id.tv_availability_index, getIndexColor(networkState.availabilityIndex.value))
                } else { views.setTextViewText(com.netweather.R.id.tv_availability_index, "--%") }
                mgr.updateAppWidget(id, views)
            }
        }
    }
    private fun getLayoutForProvider(provider: Class<*>): Int = when (provider) {
        SmallWidgetProvider::class.java -> com.netweather.R.layout.widget_small
        MediumWidgetProvider::class.java -> com.netweather.R.layout.widget_medium
        else -> com.netweather.R.layout.widget_large
    }
}
''')

w(f"{JAVA}/widget/SmallWidgetProvider.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class SmallWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {}
}
''')

w(f"{JAVA}/widget/MediumWidgetProvider.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class MediumWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {}
}
''')

w(f"{JAVA}/widget/LargeWidgetProvider.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class LargeWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {}
}
''')

w(f"{JAVA}/widget/WidgetUpdateWorker.kt", '''package com.netweather.widget

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class WidgetUpdateWorker @AssistedInject constructor(@Assisted context: Context, @Assisted workerParams: WorkerParameters) : CoroutineWorker(context, workerParams) {
    override suspend fun doWork(): Result { WidgetUtils.updateAllWidgets(applicationContext, null); return Result.success() }
    companion object {
        fun enqueuePeriodicUpdate(context: Context) {
            val workRequest = PeriodicWorkRequestBuilder<WidgetUpdateWorker>(30, TimeUnit.MINUTES).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork("widget_update", ExistingPeriodicWorkPolicy.KEEP, workRequest)
        }
        fun cancelPeriodicUpdate(context: Context) { WorkManager.getInstance(context).cancelUniqueWork("widget_update") }
        fun enqueueUpdate(context: Context) { WorkManager.getInstance(context).enqueue(OneTimeWorkRequestBuilder<WidgetUpdateWorker>().build()) }
    }
}
''')

print("✅ Widgets created")

# ============================================
# RESOURCES (XML)
# ============================================
w(f"{RES}/values/strings.xml", '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">NetWeather</string>
    <string name="widget_small_label">NetWeather Small</string>
    <string name="widget_medium_label">NetWeather Medium</string>
    <string name="widget_large_label">NetWeather Large</string>
</resources>
''')

w(f"{RES}/values/themes.xml", '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.NetWeather" parent="android:Theme.Material.Light.NoActionBar">
        <item name="android:statusBarColor">@android:color/transparent</item>
    </style>
</resources>
''')

w(f"{RES}/values/colors.xml", '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="widget_background">#FFFFFFFF</color>
    <color name="widget_text_primary">#FF191C1A</color>
    <color name="widget_text_secondary">#FF707973</color>
    <color name="ic_launcher_background">#006C4C</color>
</resources>
''')

w(f"{RES}/xml/data_extraction_rules.xml", '''<?xml version="1.0" encoding="utf-8"?>
<data-extraction-rules>
    <cloud-backup><include domain="sharedpref" path="."/></cloud-backup>
</data-extraction-rules>
''')

w(f"{RES}/xml/backup_rules.xml", '''<?xml version="1.0" encoding="utf-8"?>
<full-backup-content>
    <include domain="sharedpref" path="."/>
</full-backup-content>
''')

w(f"{RES}/xml/widget_small_info.xml", '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp" android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_small"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

w(f"{RES}/xml/widget_medium_info.xml", '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp" android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_medium"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

w(f"{RES}/xml/widget_large_info.xml", '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp" android:minHeight="250dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_large"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

w(f"{RES}/drawable/ic_launcher_foreground.xml", '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#FFFFFF"
        android:pathData="M72,58c0,-6.6 -5.4,-12 -12,-12c-0.7,0 -1.4,0.1 -2,0.2C56.6,39.5 50,34 42,34c-8.8,0 -16,7.2 -16,16c0,0.5 0,1 0.1,1.5C22.4,52.6 20,56 20,60c0,5.5 4.5,10 10,10h40C75.5,70 80,65.5 80,60C80,54.5 76.5,50 72,50z"/>
</vector>
''')

w(f"{RES}/drawable/ic_launcher_background.xml", '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#006C4C" android:pathData="M0,0h108v108h-108z"/>
</vector>
''')

w(f"{RES}/drawable/widget_background.xml", '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="@color/widget_background" />
    <corners android:radius="16dp" />
</shape>
''')

w(f"{RES}/drawable/ic_notification.xml", '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp"
    android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFF"
        android:pathData="M12,2C6.48,2 2,6.48 2,12s4.48,10 10,10 10,-4.48 10,-10S17.52,2 12,2zM12,20c-4.41,0 -8,-3.59 -8,-8s3.59,-8 8,-8 8,3.59 8,8 -3.59,8 -8,8z"/>
</vector>
''')

w(f"{RES}/drawable/ic_home.xml", '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp"
    android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFF"
        android:pathData="M10,20v-6h4v6h5v-8h3L12,3 2,12h3v8z"/>
</vector>
''')

w(f"{RES}/drawable/ic_history.xml", '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp"
    android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFF"
        android:pathData="M13,3c-4.97,0 -9,4.03 -9,9H1l3.89,3.89 0.07,0.14L9,12H6c0,-3.87 3.13,-7 7,-7s7,3.13 7,7 -3.13,7 -7,7c-1.93,0 -3.68,-0.79 -4.94,-2.06l-1.42,1.42C8.27,19.99 10.51,21 13,21c4.97,0 9,-4.03 9,-9s-4.03,-9 -9,-9zM12,8v5l4.28,2.54 0.72,-1.21 -3.5,-2.08V8H12z"/>
</vector>
''')

w(f"{RES}/drawable/ic_settings.xml", '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp"
    android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FFFFFF"
        android:pathData="M19.14,12.94c0.04,-0.3 0.06,-0.61 0.06,-0.94 0,-0.32 -0.02,-0.64 -0.07,-0.94l2.03,-1.58c0.18,-0.14 0.23,-0.41 0.12,-0.61l-1.92,-3.32c-0.12,-0.22 -0.37,-0.29 -0.59,-0.22l-2.39,0.96c-0.5,-0.38 -1.03,-0.7 -1.62,-0.94L14.4,2.81c-0.04,-0.24 -0.24,-0.41 -0.48,-0.41h-3.84c-0.24,0 -0.43,0.17 -0.47,0.41L9.25,5.35C8.66,5.59 8.12,5.92 7.63,6.29L5.24,5.33c-0.22,-0.08 -0.47,0 -0.59,0.22L2.73,8.87C2.62,9.08 2.66,9.34 2.86,9.48l2.03,1.58C4.84,11.36 4.8,11.69 4.8,12s0.02,0.64 0.07,0.94l-2.03,1.58c-0.18,0.14 -0.23,0.41 -0.12,0.61l1.92,3.32c0.12,0.22 0.37,0.29 0.59,0.22l2.39,-0.96c0.5,0.38 1.03,0.7 1.62,0.94l0.36,2.54c0.05,0.24 0.24,0.41 0.48,0.41h3.84c0.24,0 0.44,-0.17 0.47,-0.41l0.36,-2.54c0.59,-0.24 1.13,-0.56 1.62,-0.94l2.39,0.96c0.22,0.08 0.47,0 0.59,-0.22l1.92,-3.32c0.12,-0.22 0.07,-0.49 -0.12,-0.61L19.14,12.94zM12,15.6c-1.98,0 -3.6,-1.62 -3.6,-3.6s1.62,-3.6 3.6,-3.6 3.6,1.62 3.6,3.6 -1.62,3.6 -3.6,3.6z"/>
</vector>
''')

w(f"{RES}/mipmap-anydpi-v26/ic_launcher.xml", '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
''')

w(f"{RES}/mipmap-anydpi-v26/ic_launcher_round.xml", '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
</adaptive-icon>
''')

w(f"{RES}/layout/widget_small.xml", '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:background="@drawable/widget_background"
    android:gravity="center" android:orientation="vertical" android:padding="12dp">
    <TextView android:id="@+id/tv_availability_index"
        android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="0%" android:textSize="48sp" android:textStyle="bold"
        android:textColor="@color/widget_text_primary" />
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="Availability" android:textSize="12sp"
        android:textColor="@color/widget_text_secondary" />
</LinearLayout>
''')

w(f"{RES}/layout/widget_medium.xml", '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:background="@drawable/widget_background"
    android:orientation="vertical" android:padding="16dp">
    <TextView android:id="@+id/tv_availability_index"
        android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="0%" android:textSize="36sp" android:textStyle="bold"
        android:textColor="@color/widget_text_primary" />
</LinearLayout>
''')

w(f"{RES}/layout/widget_large.xml", '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent" android:layout_height="match_parent"
    android:background="@drawable/widget_background"
    android:orientation="vertical" android:padding="16dp">
    <TextView android:id="@+id/tv_availability_index"
        android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="0%" android:textSize="42sp" android:textStyle="bold"
        android:textColor="@color/widget_text_primary" />
</LinearLayout>
''')

print("✅ Resources created")

# ============================================
# ЗАВЕРШЕНИЕ
# ============================================
print("\n" + "=" * 60)
print("✅✅✅ ПРОЕКТ ПОЛНОСТЬЮ СОЗДАН ✅✅✅")
print("=" * 60)
print("\nТеперь нужно:")
print("1. Обновить build.yml чтобы он запускал этот скрипт")
print("2. Запустить сборку")