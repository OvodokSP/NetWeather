package com.netweather.domain.repository

import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import kotlinx.coroutines.flow.Flow

/**
 * Интерфейс репозитория для выполнения диагностики ресурсов
 */
interface DiagnosticsRepository {
    
    suspend fun checkResource(resource: Resource): CheckResult
    
    suspend fun checkDns(resource: Resource): CheckResult
    
    suspend fun checkTcp(resource: Resource): CheckResult
    
    suspend fun checkTls(resource: Resource): CheckResult
    
    suspend fun checkHttp(resource: Resource, useHead: Boolean = false): CheckResult
    
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