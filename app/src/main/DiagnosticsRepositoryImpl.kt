package com.netweather.data.repository

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
    override suspend fun checkDns(resource: Resource): CheckResult = networkDiagnostics.performFullDiagnostics(resource) // Упрощено
    override suspend fun checkTcp(resource: Resource): CheckResult = networkDiagnostics.performFullDiagnostics(resource)
    override suspend fun checkTls(resource: Resource): CheckResult = networkDiagnostics.performFullDiagnostics(resource)
    override suspend fun checkHttp(resource: Resource, useHead: Boolean): CheckResult = networkDiagnostics.performFullDiagnostics(resource)
    
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