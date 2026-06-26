package io.netweather.app.domain.repository

import io.netweather.app.domain.model.*
import kotlinx.coroutines.flow.Flow

interface NetWeatherRepository {
    fun observeResources(): Flow<List<MonitoredResource>>
    suspend fun getResources(): List<MonitoredResource>
    suspend fun addResource(resource: MonitoredResource): Long
    suspend fun deleteResource(resource: MonitoredResource)
    suspend fun setEnabled(id: Long, enabled: Boolean)
    suspend fun runChecks(): NetworkSummary
    suspend fun latestResults(): List<CheckResult>
    fun observeHistory(periodMillis: Long): Flow<List<NetworkSummary>>
    suspend fun ensureDefaultResources()
    suspend fun exportResourcesJson(): String
    suspend fun importResourcesJson(json: String): Int
}
