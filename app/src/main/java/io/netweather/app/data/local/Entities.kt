package io.netweather.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import io.netweather.app.domain.model.*

@Entity(tableName = "resources")
data class ResourceEntity(@PrimaryKey(autoGenerate = true) val id: Long = 0, val name: String, val url: String, val group: ResourceGroup, val method: CheckMethod, val intervalSeconds: Int, val priority: Int, val enabled: Boolean)

@Entity(tableName = "check_results")
data class CheckResultEntity(@PrimaryKey(autoGenerate = true) val id: Long = 0, val resourceId: Long, val status: DiagnosticStatus, val responseTimeMs: Long, val timestamp: Long, val lastSuccessfulCheck: Long?, val message: String)

@Entity(tableName = "history")
data class HistoryEntity(@PrimaryKey(autoGenerate = true) val id: Long = 0, val timestamp: Long, val availabilityIndex: Int, val mode: NetworkMode, val total: Int, val available: Int, val problematic: Int)

fun ResourceEntity.toDomain() = MonitoredResource(id, name, url, group, method, intervalSeconds, priority, enabled)
fun MonitoredResource.toEntity() = ResourceEntity(id, name, url, group, method, intervalSeconds, priority, enabled)
fun CheckResultEntity.toDomain() = CheckResult(resourceId, status, responseTimeMs, timestamp, lastSuccessfulCheck, message)
fun CheckResult.toEntity() = CheckResultEntity(resourceId = resourceId, status = status, responseTimeMs = responseTimeMs, timestamp = timestamp, lastSuccessfulCheck = lastSuccessfulCheck, message = message)
