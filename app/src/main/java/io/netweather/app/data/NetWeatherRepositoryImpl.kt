package io.netweather.app.data

import android.content.Context
import io.netweather.app.data.local.*
import io.netweather.app.data.network.NetworkDiagnostics
import io.netweather.app.data.network.NetWeatherApi
import io.netweather.app.domain.logic.NetworkAnalyzer
import io.netweather.app.domain.model.*
import io.netweather.app.domain.repository.NetWeatherRepository
import io.netweather.app.notification.AppNotifier
import io.netweather.app.widget.WidgetUpdater
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json

class NetWeatherRepositoryImpl(
    private val context: Context,
    private val db: AppDatabase,
    private val diagnostics: NetworkDiagnostics,
    private val api: NetWeatherApi,
    private val analyzer: NetworkAnalyzer,
    private val stateStore: StateStore,
    private val notifier: AppNotifier
) : NetWeatherRepository {
    override fun observeResources(): Flow<List<MonitoredResource>> = db.resourceDao().observeAll().map { it.map(ResourceEntity::toDomain) }
    override suspend fun getResources(): List<MonitoredResource> = db.resourceDao().getAll().map { it.toDomain() }
    override suspend fun addResource(resource: MonitoredResource): Long {
        val id = api.addResource(resource)
        refreshGlobal()
        return id
    }
    override suspend fun deleteResource(resource: MonitoredResource) = db.resourceDao().delete(resource.toEntity())
    override suspend fun setEnabled(id: Long, enabled: Boolean) = db.resourceDao().setEnabled(id, enabled)
    override suspend fun latestResults(): List<CheckResult> = db.checkResultDao().latest().map { it.toDomain() }
    override fun observeLatestResults(): Flow<List<CheckResult>> = db.checkResultDao().observeLatest().map { list -> list.map { it.toDomain() } }
    override fun observeHistory(periodMillis: Long): Flow<List<NetworkSummary>> = db.historyDao().observeSince(System.currentTimeMillis() - periodMillis).map { list -> list.map { NetworkSummary(it.availabilityIndex, it.mode, it.timestamp, it.total, it.available, it.problematic) } }
    override fun checkIntervalSeconds(): Int = stateStore.loadIntervalSeconds()
    override fun setCheckIntervalSeconds(seconds: Int) = stateStore.saveIntervalSeconds(seconds)

    override suspend fun refreshGlobal(): GlobalState {
        val remote = api.dashboard()
        syncRemoteResources(remote)
        return remote.global
    }

    private suspend fun syncRemoteResources(remote: io.netweather.app.data.network.RemoteDashboard): Set<Long> {
        remote.resources.forEach { item ->
            db.resourceDao().upsert(MonitoredResource(
                id = item.id,
                name = item.name,
                url = item.target,
                group = item.group,
                intervalSeconds = item.intervalSeconds,
                enabled = item.enabled,
            ).toEntity())
        }
        return remote.resources.mapTo(mutableSetOf()) { it.id }
    }

    override suspend fun runChecks(): NetworkSummary {
        val synchronizedResourceIds = runCatching {
            if (stateStore.accessToken() != null) syncRemoteResources(api.clientProbeResources())
            else syncRemoteResources(api.dashboard())
        }
            .onFailure { ensureDefaultResources() }
            .getOrDefault(emptySet())
        val resources = db.resourceDao().getEnabled().map { it.toDomain() }
        val previous = latestResults().associateBy { it.resourceId }
        val results = coroutineScope { resources.map { r -> async { diagnostics.check(r) } }.map { it.await() } }
        results.forEach { result ->
            val lastOk = if (result.isOk) result.timestamp else db.checkResultDao().lastSuccess(result.resourceId)?.timestamp
            db.checkResultDao().insert(result.copy(lastSuccessfulCheck = lastOk).toEntity())
        }
        if (stateStore.accessToken() != null) {
            results.filter { it.resourceId in synchronizedResourceIds }
                .forEach { result -> runCatching { api.uploadResult(result) } }
        }
        val summary = analyzer.summarize(resources, results)
        db.historyDao().insert(HistoryEntity(timestamp = summary.lastUpdated, availabilityIndex = summary.availabilityIndex, mode = summary.mode, total = summary.total, available = summary.available, problematic = summary.problematic))
        stateStore.save(summary)
        WidgetUpdater.updateAll(context, summary)
        notifier.notifyChanges(resources, previous, results)
        return summary
    }

    override suspend fun exportResourcesJson(): String = Json { prettyPrint = true }.encodeToString(getResources())

    override suspend fun importResourcesJson(json: String): Int {
        val imported = Json.decodeFromString<List<MonitoredResource>>(json)
        imported.forEach { db.resourceDao().upsert(it.copy(id = 0).toEntity()) }
        return imported.size
    }

    override fun devicePairing(): DevicePairingState = stateStore.loadPairing()
    override suspend fun startDevicePairing(): DevicePairingState = api.startPairing()
    override suspend fun pollDevicePairing(state: DevicePairingState): DevicePairingState = api.pollPairing(state)

    override suspend fun ensureDefaultResources() {
        if (db.resourceDao().count() > 0) return
        val defaults = listOf(
            MonitoredResource(name="Яндекс", url="https://yandex.ru", group=ResourceGroup.RUSSIAN, priority=100),
            MonitoredResource(name="VK", url="https://vk.com", group=ResourceGroup.RUSSIAN, priority=90),
            MonitoredResource(name="Госуслуги", url="https://gosuslugi.ru", group=ResourceGroup.RUSSIAN, priority=80),
            MonitoredResource(name="Mail.ru", url="https://mail.ru", group=ResourceGroup.RUSSIAN, priority=70),
            MonitoredResource(name="Rutube", url="https://rutube.ru", group=ResourceGroup.RUSSIAN, priority=60),
            MonitoredResource(name="YouTube", url="https://youtube.com", group=ResourceGroup.INTERNATIONAL, priority=100),
            MonitoredResource(name="Reddit", url="https://reddit.com", group=ResourceGroup.INTERNATIONAL, priority=90),
            MonitoredResource(name="Instagram", url="https://instagram.com", group=ResourceGroup.INTERNATIONAL, priority=80),
            MonitoredResource(name="Telegram", url="https://telegram.org", group=ResourceGroup.INTERNATIONAL, priority=70),
            MonitoredResource(name="Discord", url="https://discord.com", group=ResourceGroup.INTERNATIONAL, priority=60),
            MonitoredResource(name="GitHub", url="https://github.com", group=ResourceGroup.INTERNATIONAL, priority=50),
            MonitoredResource(name="Wikipedia", url="https://wikipedia.org", group=ResourceGroup.INTERNATIONAL, priority=40)
        )
        defaults.forEach { db.resourceDao().upsert(it.toEntity()) }
    }
}
