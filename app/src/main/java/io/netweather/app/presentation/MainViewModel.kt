package io.netweather.app.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.netweather.app.domain.model.*
import io.netweather.app.domain.repository.NetWeatherRepository
import io.netweather.app.worker.MonitoringScheduler
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(private val repo: NetWeatherRepository) : ViewModel() {
    private val _summary = MutableStateFlow(NetworkSummary())
    val summary: StateFlow<NetworkSummary> = _summary.asStateFlow()
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()
    private val _global = MutableStateFlow(GlobalState())
    val global: StateFlow<GlobalState> = _global.asStateFlow()
    private val _pairing = MutableStateFlow(repo.devicePairing())
    val pairing: StateFlow<DevicePairingState> = _pairing.asStateFlow()
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    val resources: StateFlow<List<ResourceWithResult>> = combine(repo.observeResources(), repo.observeLatestResults()) { res, results ->
        val map = results.associateBy { it.resourceId }
        res.map { ResourceWithResult(it, map[it.id]) }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _settings = MutableStateFlow(Settings(checkIntervalSeconds = repo.checkIntervalSeconds()))
    val settings = _settings.asStateFlow()
    val historyDay = repo.observeHistory(24L * 60L * 60L * 1000L).stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    init {
        viewModelScope.launch { refreshNow() }
        if (_pairing.value.status == "pending") pollPairing()
    }

    fun refreshNow() = viewModelScope.launch {
        _loading.value = true; _error.value = null
        try {
            _global.value = runCatching { repo.refreshGlobal() }.getOrElse { GlobalState(error = it.message) }
            _summary.value = repo.runChecks()
        } catch (e: Exception) { _error.value = e.message ?: "Ошибка проверки" } finally { _loading.value = false }
    }
    fun toggle(id: Long, enabled: Boolean) = viewModelScope.launch { repo.setEnabled(id, enabled); refreshNow() }
    fun addResource(name: String, url: String, group: ResourceGroup) = viewModelScope.launch {
        _error.value = null
        try {
            repo.addResource(MonitoredResource(name = name, url = url, group = group))
            refreshNow()
        } catch (e: Exception) {
            _error.value = e.message ?: "Не удалось добавить ресурс"
        }
    }
    fun delete(resource: MonitoredResource) = viewModelScope.launch { repo.deleteResource(resource); refreshNow() }
    fun setInterval(seconds: Int) { repo.setCheckIntervalSeconds(seconds); _settings.value = _settings.value.copy(checkIntervalSeconds = seconds); MonitoringScheduler.reschedule(AppContextHolder.context, seconds) }
    private val _exportJson = MutableStateFlow("")
    val exportJson = _exportJson.asStateFlow()
    fun exportResources() = viewModelScope.launch { _exportJson.value = repo.exportResourcesJson() }
    fun importResources(json: String) = viewModelScope.launch { try { repo.importResourcesJson(json); refreshNow() } catch (e: Exception) { _error.value = e.message ?: "Ошибка импорта" } }
    fun clearError() { _error.value = null }
    fun startPairing() = viewModelScope.launch {
        _error.value = null
        try {
            _pairing.value = repo.startDevicePairing()
            pollPairing()
        } catch (e: Exception) { _error.value = e.message ?: "Не удалось начать привязку" }
    }
    private fun pollPairing() = viewModelScope.launch {
        while (_pairing.value.status == "pending" && _pairing.value.expiresAtSeconds * 1000 > System.currentTimeMillis()) {
            kotlinx.coroutines.delay(5000)
            try {
                _pairing.value = repo.pollDevicePairing(_pairing.value)
                if (_pairing.value.status == "authorized") {
                    refreshNow()
                    break
                }
            } catch (e: Exception) {
                _error.value = e.message ?: "Не удалось проверить код"
                break
            }
        }
        if (_pairing.value.status == "pending" && _pairing.value.expiresAtSeconds * 1000 <= System.currentTimeMillis()) {
            _pairing.value = _pairing.value.copy(status = "expired")
        }
    }
}

object AppContextHolder { lateinit var context: android.content.Context }
