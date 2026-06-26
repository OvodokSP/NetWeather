#!/usr/bin/env python3
import os

JAVA = "app/src/main/java/com/netweather"

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed: {path}")

# 1. NetworkDiagnostics.kt - исправление передачи Response вместо String
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
            if (httpResult.first != DiagnosticStatus.OK) return@withContext createResult(resource, startTime, dnsResult, tcpResult, tlsResult, httpResult.first, DiagnosticStatus.UNKNOWN_ERROR, "HTTP failed")
            
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

# 2. AddResourceUseCase.kt - исправление return в expression body
w(f"{JAVA}/domain/usecase/AddResourceUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.repository.ResourceRepository
import javax.inject.Inject

class AddResourceUseCase @Inject constructor(private val resourceRepository: ResourceRepository) {
    suspend operator fun invoke(name: String, url: String, group: ResourceGroup): Result<Long> {
        return try {
            if (name.isBlank()) return Result.failure(IllegalArgumentException("Name is empty"))
            val normalizedUrl = if (url.startsWith("http://") || url.startsWith("https://")) url else "https://$url"
            if (resourceRepository.resourceExists(normalizedUrl)) return Result.failure(IllegalStateException("Resource exists"))
            val resource = Resource(name = name.trim(), url = normalizedUrl, group = group, enabled = true)
            Result.success(resourceRepository.addResource(resource))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
''')

# 3. CalculateAvailabilityIndexUseCase.kt - исправление return
w(f"{JAVA}/domain/usecase/CalculateAvailabilityIndexUseCase.kt", '''package com.netweather.domain.usecase

import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import javax.inject.Inject

class CalculateAvailabilityIndexUseCase @Inject constructor() {
    suspend operator fun invoke(resources: List<Resource>, checkResults: List<CheckResult>): Result<AvailabilityIndex> {
        return try {
            if (resources.isEmpty()) return Result.success(AvailabilityIndex.create(0))
            val resultsMap = checkResults.associateBy { it.resourceId }
            val availableCount = resources.count { r -> resultsMap[r.id]?.isSuccessful() == true }
            val index = (availableCount * 100) / resources.size
            Result.success(AvailabilityIndex.create(index))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
''')

# 4. CheckAllResourcesUseCase.kt - исправление return
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
    suspend operator fun invoke(): Result<List<CheckResult>> {
        return try {
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
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun checkAllOnce(): Result<List<CheckResult>> = invoke()
}
''')

# 5. MainScreen.kt - убираем PullToRefreshBox (нет в старой версии Material3)
w(f"{JAVA}/presentation/main/MainScreen.kt", '''package com.netweather.presentation.main

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
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
        Box(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
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

# 6. NetworkMode.kt - добавляем getDescription()
w(f"{JAVA}/domain/model/NetworkMode.kt", '''package com.netweather.domain.model

enum class NetworkMode {
    NORMAL, PARTIAL_DEGRADATION, RESTRICTED_ACCESS, NO_INTERNET;
    fun getEmoji(): String = when (this) { NORMAL -> "🟢"; PARTIAL_DEGRADATION -> "🟡"; RESTRICTED_ACCESS -> "🟠"; NO_INTERNET -> "🔴" }
    fun getTitle(): String = when (this) { NORMAL -> "Normal"; PARTIAL_DEGRADATION -> "Partial"; RESTRICTED_ACCESS -> "Restricted"; NO_INTERNET -> "No internet" }
    fun getDescription(): String = when (this) { NORMAL -> "All resources are available"; PARTIAL_DEGRADATION -> "Some resources are unavailable"; RESTRICTED_ACCESS -> "Access to some resources is restricted"; NO_INTERNET -> "No internet connection" }
    fun getShortDescription(): String = when (this) { NORMAL -> "All OK"; PARTIAL_DEGRADATION -> "Some issues"; RESTRICTED_ACCESS -> "Restricted"; NO_INTERNET -> "No internet" }
}
''')

# 7. SettingsScreen.kt - исправляем вызовы ThemeSelector и IntervalSelector
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
            item { ThemeSelector(currentTheme = uiState.settings.themeMode, onThemeSelected = { viewModel.setThemeMode(it) }) }
            item { Text("Check interval", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { IntervalSelector(currentInterval = uiState.settings.checkIntervalMinutes, onIntervalSelected = { viewModel.setCheckInterval(it) }) }
            item { Text("Notifications", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { NotificationsSettings(settings = uiState.settings, onMain = viewModel::setNotificationsEnabled, onFailure = viewModel::setNotifyOnFailure, onRecovery = viewModel::setNotifyOnRecovery, onSlow = viewModel::setNotifyOnSlowResponse) }
            item { Text("Resources", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { ResourceGroupManager(ru = uiState.russianResources, intl = uiState.internationalResources, custom = uiState.customResources, onToggle = viewModel::toggleResource, onDelete = viewModel::deleteResource, onAdd = viewModel::addCustomResource) }
            item { Spacer(Modifier.height(16.dp)); OutlinedButton(onClick = { viewModel.resetSettings() }, modifier = Modifier.fillMaxWidth()) { Text("Reset settings") } }
        }
    }
}
''')

print("\n✅✅✅ ALL ERRORS FIXED ✅✅✅")
print("Now commit and push, then run the build again!")