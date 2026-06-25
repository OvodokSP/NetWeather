#!/usr/bin/env python3
"""
Скрипт для исправления структуры проекта NetWeather
Перемещает все файлы в правильные папки и создаёт недостающие файлы
"""
import os
import shutil

BASE = "app/src/main"
JAVA = f"{BASE}/java/com/netweather"
RES = f"{BASE}/res"

# ============================================
# 1. ПЕРЕМЕЩЕНИЕ KOTLIN ФАЙЛОВ
# ============================================
kotlin_moves = {
    # Domain - Models
    "Resource.kt": f"{JAVA}/domain/model/",
    "DiagnosticStatus.kt": f"{JAVA}/domain/model/",
    "CheckResult.kt": f"{JAVA}/domain/model/",
    "NetworkMode.kt": f"{JAVA}/domain/model/",
    "AvailabilityIndex.kt": f"{JAVA}/domain/model/",
    "HistoryEntry.kt": f"{JAVA}/domain/model/",
    "NetworkState.kt": f"{JAVA}/domain/model/",
    "Settings.kt": f"{JAVA}/domain/model/",
    
    # Domain - Repository interfaces
    "ResourceRepository.kt": f"{JAVA}/domain/repository/",
    "DiagnosticsRepository.kt": f"{JAVA}/domain/repository/",
    "HistoryRepository.kt": f"{JAVA}/domain/repository/",
    "SettingsRepository.kt": f"{JAVA}/domain/repository/",
    
    # Domain - Use Cases
    "CheckResourceUseCase.kt": f"{JAVA}/domain/usecase/",
    "CheckAllResourcesUseCase.kt": f"{JAVA}/domain/usecase/",
    "CalculateAvailabilityIndexUseCase.kt": f"{JAVA}/domain/usecase/",
    "DetermineNetworkModeUseCase.kt": f"{JAVA}/domain/usecase/",
    "GetHistoryUseCase.kt": f"{JAVA}/domain/usecase/",
    "AddResourceUseCase.kt": f"{JAVA}/domain/usecase/",
    "DeleteResourceUseCase.kt": f"{JAVA}/domain/usecase/",
    "ExportImportUseCase.kt": f"{JAVA}/domain/usecase/",
    
    # Data - Local DB
    "AppDatabase.kt": f"{JAVA}/data/local/db/",
    "ResourceDao.kt": f"{JAVA}/data/local/db/dao/",
    "CheckResultDao.kt": f"{JAVA}/data/local/db/dao/",
    "HistoryDao.kt": f"{JAVA}/data/local/db/dao/",
    "ResourceEntity.kt": f"{JAVA}/data/local/db/entity/",
    "CheckResultEntity.kt": f"{JAVA}/data/local/db/entity/",
    "HistoryEntity.kt": f"{JAVA}/data/local/db/entity/",
    
    # Data - Local Preferences
    "PreferencesManager.kt": f"{JAVA}/data/local/preferences/",
    
    # Data - Remote
    "NetworkClient.kt": f"{JAVA}/data/remote/",
    "NetworkDiagnostics.kt": f"{JAVA}/data/remote/",
    
    # Data - Repository implementations
    "ResourceRepositoryImpl.kt": f"{JAVA}/data/repository/",
    "DiagnosticsRepositoryImpl.kt": f"{JAVA}/data/repository/",
    "HistoryRepositoryImpl.kt": f"{JAVA}/data/repository/",
    "SettingsRepositoryImpl.kt": f"{JAVA}/data/repository/",
    
    # DI
    "AppModule.kt": f"{JAVA}/di/",
    "DatabaseModule.kt": f"{JAVA}/di/",
    "NetworkModule.kt": f"{JAVA}/di/",
    "RepositoryModule.kt": f"{JAVA}/di/",
    
    # Presentation - Main
    "MainScreen.kt": f"{JAVA}/presentation/main/",
    "MainViewModel.kt": f"{JAVA}/presentation/main/",
    
    # Presentation - Main Components
    "AvailabilityIndexCard.kt": f"{JAVA}/presentation/main/components/",
    "NetworkModeCard.kt": f"{JAVA}/presentation/main/components/",
    "ResourceGroupSection.kt": f"{JAVA}/presentation/main/components/",
    "ResourceItem.kt": f"{JAVA}/presentation/main/components/",
    
    # Presentation - Theme
    "Color.kt": f"{JAVA}/presentation/theme/",
    "Type.kt": f"{JAVA}/presentation/theme/",
    "Theme.kt": f"{JAVA}/presentation/theme/",
    "Shape.kt": f"{JAVA}/presentation/theme/",
    
    # App root
    "NetWeatherApp.kt": f"{JAVA}/",
}

# ============================================
# 2. ПЕРЕМЕЩЕНИЕ XML РЕСУРСОВ
# ============================================
xml_moves = {
    "strings.xml": f"{RES}/values/",
    "themes.xml": f"{RES}/values/",
    "colors.xml": f"{RES}/values/",
    "ic_launcher_background.xml": f"{RES}/values/",
    "backup_rules.xml": f"{RES}/xml/",
    "data_extraction_rules.xml": f"{RES}/xml/",
    "ic_home.xml": f"{RES}/drawable/",
    "ic_history.xml": f"{RES}/drawable/",
    "ic_settings.xml": f"{RES}/drawable/",
    "ic_notification.xml": f"{RES}/drawable/",
}

# ============================================
# 3. ВЫПОЛНЕНИЕ ПЕРЕМЕЩЕНИЙ
# ============================================
def move_files(moves_dict, base_dir):
    moved = 0
    for filename, dest_dir in moves_dict.items():
        src = os.path.join(base_dir, filename)
        dst_dir = dest_dir
        dst = os.path.join(dst_dir, filename)
        
        if os.path.exists(src):
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, dst)
            print(f"  ✅ {filename} → {dst_dir}")
            moved += 1
        else:
            print(f"  ⚠️  {filename} не найден в {base_dir}")
    return moved

print("=" * 60)
print("🔧 ИСПРАВЛЕНИЕ СТРУКТУРЫ ПРОЕКТА NetWeather")
print("=" * 60)

print("\n📦 Перемещение Kotlin файлов...")
moved_kotlin = move_files(kotlin_moves, BASE)
print(f"   Перемещено: {moved_kotlin}")

print("\n🎨 Перемещение XML ресурсов...")
moved_xml = move_files(xml_moves, BASE)
print(f"   Перемещено: {moved_xml}")

# ============================================
# 4. СОЗДАНИЕ НЕДОСТАЮЩИХ ФАЙЛОВ
# ============================================
def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  📝 Создан: {path}")

print("\n🆕 Создание недостающих файлов...")

# MainActivity.kt
write_file(f"{JAVA}/MainActivity.kt", '''package com.netweather

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
    
    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (!isGranted) {
            android.util.Log.d("MainActivity", "Notification permission denied")
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        requestNotificationPermission()
        
        setContent {
            val settingsViewModel: SettingsViewModel = hiltViewModel()
            val uiState by settingsViewModel.uiState.collectAsState()
            
            NetWeatherTheme(themeMode = uiState.settings.themeMode) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    NetWeatherNavigation()
                }
            }
        }
    }
    
    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            when {
                ContextCompat.checkSelfPermission(
                    this, Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED -> {}
                else -> {
                    notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }
        }
    }
}
''')

# NavigationRoutes.kt
write_file(f"{JAVA}/presentation/navigation/NavigationRoutes.kt", '''package com.netweather.presentation.navigation

object NavigationRoutes {
    const val MAIN = "main"
    const val HISTORY = "history"
    const val SETTINGS = "settings"
}
''')

# Navigation.kt
write_file(f"{JAVA}/presentation/navigation/Navigation.kt", '''package com.netweather.presentation.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
    NavigationItem(NavigationRoutes.MAIN, Icons.Default.Home, "Главная"),
    NavigationItem(NavigationRoutes.HISTORY, Icons.Default.History, "История"),
    NavigationItem(NavigationRoutes.SETTINGS, Icons.Default.Settings, "Настройки")
)
''')

# HistoryScreen.kt
write_file(f"{JAVA}/presentation/history/HistoryScreen.kt", '''package com.netweather.presentation.history

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
    
    LaunchedEffect(uiState.error) {
        uiState.error?.let { error ->
            snackbarHostState.showSnackbar(message = error, actionLabel = "OK")
            viewModel.clearError()
        }
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("История", style = MaterialTheme.typography.headlineMedium) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        if (uiState.hasData()) {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(paddingValues),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                item {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        HistoryPeriod.values().forEach { period ->
                            FilterChip(
                                selected = selectedPeriod == period,
                                onClick = { viewModel.selectPeriod(period) },
                                label = { Text(period.getTitle()) },
                                modifier = Modifier.weight(1f)
                            )
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
                    Text("История пуста", style = MaterialTheme.typography.headlineSmall)
                    Text("Данные появятся после первых проверок", style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
                }
            }
        }
    }
}
''')

# HistoryViewModel.kt
write_file(f"{JAVA}/presentation/history/HistoryViewModel.kt", '''package com.netweather.presentation.history

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
class HistoryViewModel @Inject constructor(
    private val historyRepository: HistoryRepository
) : ViewModel() {
    
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
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }
    
    fun selectPeriod(period: HistoryPeriod) { _selectedPeriod.value = period; loadHistory() }
    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
}

data class HistoryUiState(
    val isLoading: Boolean = false,
    val historyEntries: List<HistoryEntry> = emptyList(),
    val statistics: HistoryStatistics? = null,
    val error: String? = null
) {
    fun hasData(): Boolean = historyEntries.isNotEmpty()
}

data class HistoryStatistics(
    val averageIndex: Int, val minIndex: Int, val maxIndex: Int, val totalEntries: Int,
    val normalCount: Int, val partialCount: Int, val restrictedCount: Int, val noInternetCount: Int
) {
    fun getModePercentages(): Map<String, Int> {
        if (totalEntries == 0) return mapOf("normal" to 0, "partial" to 0, "restricted" to 0, "noInternet" to 0)
        return mapOf(
            "normal" to (normalCount * 100) / totalEntries,
            "partial" to (partialCount * 100) / totalEntries,
            "restricted" to (restrictedCount * 100) / totalEntries,
            "noInternet" to (noInternetCount * 100) / totalEntries
        )
    }
}
''')

# History components
write_file(f"{JAVA}/presentation/history/components/HistoryChart.kt", '''package com.netweather.presentation.history.components

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
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun HistoryChart(historyEntries: List<HistoryEntry>, period: HistoryPeriod, modifier: Modifier = Modifier) {
    Card(modifier = modifier.fillMaxWidth(), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text("График доступности", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            Canvas(modifier = Modifier.fillMaxWidth().height(200.dp)) {
                if (historyEntries.isEmpty()) return@Canvas
                val sorted = historyEntries.sortedBy { it.timestamp }
                val width = size.width; val height = size.height; val padding = 40.dp.toPx()
                val chartWidth = width - padding * 2; val chartHeight = height - padding * 2
                for (i in 0..4) {
                    val y = padding + (chartHeight / 4) * i
                    drawLine(color = NetWeatherColors.chartGrid, start = Offset(padding, y), end = Offset(width - padding, y), strokeWidth = 1.dp.toPx())
                }
                val path = Path(); val fillPath = Path()
                sorted.forEachIndexed { index, entry ->
                    val x = padding + (chartWidth * index) / (sorted.size - 1).coerceAtLeast(1)
                    val y = padding + chartHeight - (chartHeight * entry.availabilityIndex / 100f)
                    if (index == 0) { path.moveTo(x, y); fillPath.moveTo(x, padding + chartHeight); fillPath.lineTo(x, y) }
                    else { path.lineTo(x, y); fillPath.lineTo(x, y) }
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

write_file(f"{JAVA}/presentation/history/components/StatisticsCard.kt", '''package com.netweather.presentation.history.components

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
            Text("Статистика", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(16.dp))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                StatValue("Средний", "${statistics.averageIndex}%", getColorForIndex(statistics.averageIndex))
                StatValue("Минимум", "${statistics.minIndex}%", getColorForIndex(statistics.minIndex))
                StatValue("Максимум", "${statistics.maxIndex}%", getColorForIndex(statistics.maxIndex))
            }
            Spacer(Modifier.height(16.dp))
            val p = statistics.getModePercentages()
            ModeDist("Нормальный", p["normal"] ?: 0, NetWeatherColors.statusNormal)
            ModeDist("Частичная деградация", p["partial"] ?: 0, NetWeatherColors.statusWarning)
            ModeDist("Ограничения доступа", p["restricted"] ?: 0, NetWeatherColors.statusRestricted)
            ModeDist("Нет интернета", p["noInternet"] ?: 0, NetWeatherColors.statusError)
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
    index >= 80 -> NetWeatherColors.statusNormal; index >= 70 -> NetWeatherColors.statusWarning
    index >= 30 -> NetWeatherColors.statusRestricted; else -> NetWeatherColors.statusError
}
''')

write_file(f"{JAVA}/presentation/history/components/HistoryItem.kt", '''package com.netweather.presentation.history.components

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
                Text("Доступно: ${entry.availableCount} | Недоступно: ${entry.unavailableCount}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("${entry.availabilityIndex}%", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, color = statusColor)
                Text("индекс", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
''')

# SettingsScreen.kt
write_file(f"{JAVA}/presentation/settings/SettingsScreen.kt", '''package com.netweather.presentation.settings

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
        topBar = { TopAppBar(title = { Text("Настройки", style = MaterialTheme.typography.headlineMedium) }, colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)) },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            item { Text("Внешний вид", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { ThemeSelector(uiState.settings.themeMode) { viewModel.setThemeMode(it) } }
            item { Text("Интервал проверки", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { IntervalSelector(uiState.settings.checkIntervalMinutes) { viewModel.setCheckInterval(it) } }
            item { Text("Уведомления", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { NotificationsSettings(uiState.settings, viewModel::setNotificationsEnabled, viewModel::setNotifyOnFailure, viewModel::setNotifyOnRecovery, viewModel::setNotifyOnSlowResponse) }
            item { Text("Ресурсы", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary) }
            item { ResourceGroupManager(uiState.russianResources, uiState.internationalResources, uiState.customResources, viewModel::toggleResource, viewModel::deleteResource, viewModel::addCustomResource) }
            item { Spacer(Modifier.height(16.dp)); OutlinedButton(onClick = { viewModel.resetSettings() }, modifier = Modifier.fillMaxWidth()) { Text("Сбросить настройки") } }
        }
    }
}
''')

# SettingsViewModel.kt
write_file(f"{JAVA}/presentation/settings/SettingsViewModel.kt", '''package com.netweather.presentation.settings

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
    fun toggleResource(id: Long) = viewModelScope.launch {
        val r = resourceRepository.getResourceById(id) ?: return@launch
        resourceRepository.setResourceEnabled(id, !r.enabled)
    }
    fun deleteResource(id: Long) = viewModelScope.launch { deleteResourceUseCase(id) }
    fun addCustomResource(name: String, url: String) = viewModelScope.launch { addResourceUseCase(name, url, ResourceGroup.CUSTOM) }
    fun resetSettings() = viewModelScope.launch { settingsRepository.resetToDefaults() }
    fun clearError() { _uiState.value = _uiState.value.copy(error = null) }
    fun clearSuccessMessage() { _uiState.value = _uiState.value.copy(successMessage = null) }
}

data class SettingsUiState(
    val settings: Settings = Settings(),
    val resources: List<Resource> = emptyList(),
    val russianResources: List<Resource> = emptyList(),
    val internationalResources: List<Resource> = emptyList(),
    val customResources: List<Resource> = emptyList(),
    val error: String? = null,
    val successMessage: String? = null
)
''')

# Settings components
write_file(f"{JAVA}/presentation/settings/components/ThemeSelector.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.ThemeMode

@Composable
fun ThemeSelector(currentTheme: ThemeMode, onThemeSelected: (ThemeMode) -> Unit, modifier: Modifier = Modifier) {
    SettingsCard("Тема приложения", modifier) {
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

write_file(f"{JAVA}/presentation/settings/components/IntervalSelector.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun IntervalSelector(currentInterval: Int, onIntervalSelected: (Int) -> Unit, modifier: Modifier = Modifier) {
    SettingsCard("Интервал проверки", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Каждые $currentInterval минут", style = MaterialTheme.typography.bodyLarge)
            Slider(value = currentInterval.toFloat(), onValueChange = { onIntervalSelected(it.toInt()) }, valueRange = 5f..60f, steps = 10)
            Text("От 5 до 60 минут", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
''')

write_file(f"{JAVA}/presentation/settings/components/NotificationsSettings.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.Settings

@Composable
fun NotificationsSettings(
    settings: Settings,
    onMain: (Boolean) -> Unit,
    onFailure: (Boolean) -> Unit,
    onRecovery: (Boolean) -> Unit,
    onSlow: (Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    SettingsCard("Уведомления", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Toggle("Включить уведомления", "Получать уведомления о состоянии сети", settings.enableNotifications, onMain)
            if (settings.enableNotifications) {
                Toggle("Уведомлять о сбоях", "Когда ресурс недоступен", settings.notifyOnFailure, onFailure)
                Toggle("Уведомлять о восстановлении", "Когда ресурс восстановлен", settings.notifyOnRecovery, onRecovery)
                Toggle("Уведомлять о медленном отклике", "Когда время отклика превышает порог", settings.notifyOnSlowResponse, onSlow)
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

write_file(f"{JAVA}/presentation/settings/components/ResourceGroupManager.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.Resource

@Composable
fun ResourceGroupManager(
    ru: List<Resource>, intl: List<Resource>, custom: List<Resource>,
    onToggle: (Long) -> Unit, onDelete: (Long) -> Unit, onAdd: (String, String) -> Unit,
    modifier: Modifier = Modifier
) {
    var showDialog by remember { mutableStateOf(false) }
    SettingsCard("Ресурсы для мониторинга", modifier) {
        Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
            GroupSection("🇷🇺 Российские", ru, onToggle)
            GroupSection("🌍 Международные", intl, onToggle)
            GroupSection("⭐ Пользовательские", custom, onToggle, onDelete)
            Button(onClick = { showDialog = true }, modifier = Modifier.fillMaxWidth()) { Text("Добавить ресурс") }
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
                if (onDelete != null && r.group == com.netweather.domain.model.ResourceGroup.CUSTOM) {
                    TextButton(onClick = { onDelete(r.id) }) { Text("Удалить", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }
}
''')

write_file(f"{JAVA}/presentation/settings/components/AddResourceDialog.kt", '''package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun AddResourceDialog(onDismiss: () -> Unit, onConfirm: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Добавить ресурс") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Название") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                OutlinedTextField(value = url, onValueChange = { url = it }, label = { Text("URL") }, placeholder = { Text("https://example.com") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            }
        },
        confirmButton = { TextButton(onClick = { if (name.isNotBlank() && url.isNotBlank()) onConfirm(name.trim(), url.trim()) }) { Text("Добавить") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } }
    )
}
''')

write_file(f"{JAVA}/presentation/settings/components/SettingsCard.kt", '''package com.netweather.presentation.settings.components

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

# Workers
write_file(f"{JAVA}/worker/WorkerScheduler.kt", '''package com.netweather.worker

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

write_file(f"{JAVA}/worker/PeriodicCheckWorker.kt", '''package com.netweather.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.netweather.domain.repository.*
import com.netweather.domain.usecase.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class PeriodicCheckWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val resourceRepository: ResourceRepository,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val historyRepository: HistoryRepository
) : CoroutineWorker(context, workerParams) {
    
    override suspend fun doWork(): Result {
        return try {
            val resources = resourceRepository.getAllResourcesOnce().filter { it.enabled }
            if (resources.isEmpty()) return Result.success()
            
            resources.forEach { resource ->
                try {
                    val result = diagnosticsRepository.checkResource(resource)
                    diagnosticsRepository.saveCheckResult(result)
                } catch (e: Exception) { e.printStackTrace() }
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

write_file(f"{JAVA}/worker/CleanupWorker.kt", '''package com.netweather.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.netweather.domain.repository.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class CleanupWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val diagnosticsRepository: DiagnosticsRepository,
    private val historyRepository: HistoryRepository,
    private val settingsRepository: SettingsRepository
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

write_file(f"{JAVA}/worker/BootReceiver.kt", '''package com.netweather.worker

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

# Notifications
write_file(f"{JAVA}/notification/NotificationManager.kt", '''package com.netweather.notification

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
    
    companion object {
        const val CHANNEL_ID_FAILURE = "resource_failure"
    }
    
    init { createChannels() }
    
    private fun createChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as AndroidNotificationManager
            manager.createNotificationChannel(NotificationChannel(CHANNEL_ID_FAILURE, "Сбои ресурсов", AndroidNotificationManager.IMPORTANCE_HIGH))
        }
    }
    
    fun notifyResourceFailure(resourceName: String, error: String) {
        val intent = Intent(context, MainActivity::class.java).apply { flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK }
        val pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_FAILURE)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Ресурс недоступен")
            .setContentText("$resourceName: $error")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
        
        try { NotificationManagerCompat.from(context).notify(System.currentTimeMillis().toInt(), notification) }
        catch (e: SecurityException) { e.printStackTrace() }
    }
}
''')

write_file(f"{JAVA}/notification/NotificationActionReceiver.kt", '''package com.netweather.notification

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class NotificationActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {}
}
''')

# Widgets
write_file(f"{JAVA}/widget/WidgetUtils.kt", '''package com.netweather.widget

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
                    views.setTextViewText(getIndexIdForProvider(provider), "${networkState.availabilityIndex.value}%")
                    views.setTextColor(getIndexIdForProvider(provider), getIndexColor(networkState.availabilityIndex.value))
                } else {
                    views.setTextViewText(getIndexIdForProvider(provider), "--%")
                }
                mgr.updateAppWidget(id, views)
            }
        }
    }
    
    private fun getLayoutForProvider(provider: Class<*>): Int = when (provider) {
        SmallWidgetProvider::class.java -> com.netweather.R.layout.widget_small
        MediumWidgetProvider::class.java -> com.netweather.R.layout.widget_medium
        else -> com.netweather.R.layout.widget_large
    }
    
    private fun getIndexIdForProvider(provider: Class<*>): Int = com.netweather.R.id.tv_availability_index
}
''')

write_file(f"{JAVA}/widget/SmallWidgetProvider.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class SmallWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {}
}
''')

write_file(f"{JAVA}/widget/MediumWidgetProvider.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class MediumWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {}
}
''')

write_file(f"{JAVA}/widget/LargeWidgetProvider.kt", '''package com.netweather.widget

import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context

class LargeWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {}
}
''')

write_file(f"{JAVA}/widget/WidgetUpdateWorker.kt", '''package com.netweather.widget

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class WidgetUpdateWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {
    override suspend fun doWork(): Result {
        WidgetUtils.updateAllWidgets(applicationContext, null)
        return Result.success()
    }
    
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

# Widget layouts
write_file(f"{RES}/layout/widget_small.xml", '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@drawable/widget_background"
    android:gravity="center"
    android:orientation="vertical"
    android:padding="12dp">
    <TextView android:id="@+id/tv_availability_index" android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="0%" android:textSize="48sp" android:textStyle="bold" android:textColor="@color/widget_text_primary" />
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="Доступность" android:textSize="12sp" android:textColor="@color/widget_text_secondary" />
</LinearLayout>
''')

write_file(f"{RES}/layout/widget_medium.xml", '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@drawable/widget_background"
    android:orientation="vertical"
    android:padding="16dp">
    <LinearLayout android:layout_width="match_parent" android:layout_height="wrap_content" android:orientation="horizontal" android:gravity="center_vertical">
        <LinearLayout android:layout_width="0dp" android:layout_height="wrap_content" android:layout_weight="1" android:orientation="vertical" android:gravity="center">
            <TextView android:id="@+id/tv_availability_index" android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="0%" android:textSize="36sp" android:textStyle="bold" android:textColor="@color/widget_text_primary" />
            <TextView android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="Доступность" android:textSize="11sp" android:textColor="@color/widget_text_secondary" />
        </LinearLayout>
    </LinearLayout>
</LinearLayout>
''')

write_file(f"{RES}/layout/widget_large.xml", '''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@drawable/widget_background"
    android:orientation="vertical"
    android:padding="16dp">
    <TextView android:id="@+id/tv_availability_index" android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="0%" android:textSize="42sp" android:textStyle="bold" android:textColor="@color/widget_text_primary" />
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content" android:text="Доступность" android:textSize="11sp" android:textColor="@color/widget_text_secondary" />
</LinearLayout>
''')

# Widget info XMLs
write_file(f"{RES}/xml/widget_small_info.xml", '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp" android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_small"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

write_file(f"{RES}/xml/widget_medium_info.xml", '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp" android:minHeight="110dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_medium"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

write_file(f"{RES}/xml/widget_large_info.xml", '''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp" android:minHeight="250dp"
    android:updatePeriodMillis="1800000"
    android:initialLayout="@layout/widget_large"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''')

# Widget background drawable
write_file(f"{RES}/drawable/widget_background.xml", '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="@color/widget_background" />
    <corners android:radius="16dp" />
</shape>
''')

print("\n" + "=" * 60)
print("✅ СТРУКТУРА ПРОЕКТА ИСПРАВЛЕНА!")
print("=" * 60)
print("\nТеперь выполните:")
print("  git add .")
print("  git commit -m 'Fix project structure'")
print("  git push origin main")