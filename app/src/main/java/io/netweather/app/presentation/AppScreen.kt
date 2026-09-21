package io.netweather.app.presentation

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import io.netweather.app.domain.model.*
import java.text.SimpleDateFormat
import java.util.*

private val CardBlue = Color(0xFF0C2238)
private val CardBlue2 = Color(0xFF102B45)
private val Muted = Color(0xFFAAB9C9)
private val Good = Color(0xFF2ECC71)
private val Warn = Color(0xFFF5B942)
private val Bad = Color(0xFFE85D5D)
private val Cyan = Color(0xFF00B4DB)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScreen(vm: MainViewModel = hiltViewModel()) {
    val summary by vm.summary.collectAsState(); val global by vm.global.collectAsState(); val loading by vm.loading.collectAsState()
    val error by vm.error.collectAsState(); val resources by vm.resources.collectAsState(); val pairing by vm.pairing.collectAsState(); val history by vm.historyDay.collectAsState()
    var tab by rememberSaveable { mutableIntStateOf(0) }; var showAdd by rememberSaveable { mutableStateOf(false) }; val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(error) { error?.let { snackbar.showSnackbar(it); vm.clearError() } }
    Scaffold(containerColor = MaterialTheme.colorScheme.background, snackbarHost = { SnackbarHost(snackbar) }, bottomBar = { BottomBar(tab) { tab = it } }, floatingActionButton = { if (tab == 0) FloatingActionButton({ showAdd = true }, containerColor = Cyan) { Icon(Icons.Outlined.Add, "Добавить ресурс") } }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) { when (tab) { 0 -> HomeTab(global, summary, resources, loading, vm::refreshNow); 1 -> HistoryTab(history); else -> SettingsTab(vm, pairing) } }
    }
    if (showAdd) AddResourceDialog({ showAdd = false }) { name, url, group -> vm.addResource(name, url, group); showAdd = false }
}

@Composable private fun BottomBar(selected: Int, onSelect: (Int) -> Unit) { NavigationBar(containerColor = Color(0xFF071827), tonalElevation = 0.dp) {
    listOf(Icons.Outlined.Home to "Главная", Icons.Outlined.AutoGraph to "История", Icons.Outlined.Settings to "Настройки").forEachIndexed { i, item ->
        NavigationBarItem(selected == i, { onSelect(i) }, icon = { Icon(item.first, item.second) }, label = { Text(item.second, fontSize = 11.sp) }, colors = NavigationBarItemDefaults.colors(selectedIconColor = Color.White, selectedTextColor = Cyan, indicatorColor = Color(0xFF12345A), unselectedIconColor = Muted, unselectedTextColor = Muted))
    }
} }

@Composable private fun Header(title: String, action: @Composable (() -> Unit)? = null) { Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 18.dp), verticalAlignment = Alignment.CenterVertically) { Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold); Spacer(Modifier.weight(1f)); action?.invoke() } }

@Composable private fun HomeTab(global: GlobalState, summary: NetworkSummary, resources: List<ResourceWithResult>, loading: Boolean, refresh: () -> Unit) { LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp, 0.dp, 16.dp, 28.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
    item { Header("Главная") { IconButton(refresh, enabled = !loading) { Icon(Icons.Outlined.Refresh, "Обновить") } } }
    item { AvailabilityCard(summary, global) }
    item { Button(refresh, enabled = !loading, modifier = Modifier.fillMaxWidth().height(52.dp), shape = RoundedCornerShape(16.dp)) { Icon(Icons.Outlined.PlayArrow, null); Spacer(Modifier.width(8.dp)); Text(if (loading) "Проверка…" else "Проверить сейчас") } }
    item { SectionHeader("Группы ресурсов", Icons.Outlined.Tune) }
    items(groupCards(resources)) { GroupCard(it) }
    item { SectionHeader("Ресурсы", Icons.Outlined.Public) }
    items(resources.take(8), key = { it.resource.id }) { ResourceRow(it) }
    if (resources.isEmpty()) item { EmptyCard("Ресурсы ещё не добавлены", "Нажмите +, чтобы начать мониторинг") }
} }

private data class GroupCardData(val group: ResourceGroup, val count: Int, val available: Int)
private fun groupCards(rows: List<ResourceWithResult>) = ResourceGroup.values().mapNotNull { group -> rows.filter { it.resource.group == group }.takeIf { it.isNotEmpty() }?.let { GroupCardData(group, it.size, it.count { row -> row.result?.isOk == true }) } }

@Composable private fun SectionHeader(title: String, icon: androidx.compose.ui.graphics.vector.ImageVector) { Row(Modifier.fillMaxWidth().padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) { Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold); Spacer(Modifier.weight(1f)); Icon(icon, null, tint = Muted) } }

@Composable private fun AvailabilityCard(summary: NetworkSummary, global: GlobalState) { val value = summary.availabilityIndex.coerceIn(0, 100); val fallback = global.availability ?: 0; val shown = if (summary.total > 0) value else fallback; val accent = if (shown >= 95) Good else if (shown >= 70) Warn else Bad
    Card(colors = CardDefaults.cardColors(CardBlue), shape = RoundedCornerShape(24.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp)) { Text("Общая доступность", style = MaterialTheme.typography.titleMedium); Spacer(Modifier.height(8.dp)); Row(verticalAlignment = Alignment.CenterVertically) { AvailabilityRing(shown, accent, Modifier.size(150.dp)); Spacer(Modifier.width(18.dp)); Column(verticalArrangement = Arrangement.spacedBy(10.dp)) { Legend(Good, "Доступно", if (summary.total > 0) summary.available else fallback); Legend(Warn, "Проблемы", summary.problematic); Legend(Bad, "Недоступно", (summary.total - summary.available - summary.problematic).coerceAtLeast(0)); Legend(Cyan, "Проверка", if (summary.lastUpdated == 0L) 1 else 0) } }; Spacer(Modifier.height(6.dp)); Text(if (summary.lastUpdated > 0) "Обновлено ${formatTime(summary.lastUpdated)}" else "Ожидание первой локальной проверки", color = Muted, fontSize = 12.sp) } }
}

@Composable private fun AvailabilityRing(value: Int, color: Color, modifier: Modifier) { Box(modifier, contentAlignment = Alignment.Center) { Canvas(Modifier.fillMaxSize().padding(8.dp)) { drawArc(Color(0xFF1C3850), -90f, 360f, false, style = Stroke(18f, cap = StrokeCap.Round)); drawArc(color, -90f, 360f * value / 100f, false, style = Stroke(18f, cap = StrokeCap.Round)) }; Column(horizontalAlignment = Alignment.CenterHorizontally) { Text("$value%", fontSize = 28.sp, fontWeight = FontWeight.Bold); Text("онлайн", color = Muted, fontSize = 12.sp) } } }
@Composable private fun Legend(color: Color, label: String, value: Int) { Row(verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(10.dp).clip(CircleShape).background(color)); Spacer(Modifier.width(8.dp)); Text("$label  $value", fontSize = 13.sp) } }

@Composable private fun GroupCard(data: GroupCardData) { val percentage = if (data.count == 0) 0 else data.available * 100 / data.count; val color = if (percentage >= 95) Good else if (percentage >= 70) Warn else Bad; Card(colors = CardDefaults.cardColors(CardBlue2), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Outlined.Language, null, tint = Color(0xFF4FA3FF), modifier = Modifier.size(28.dp)); Spacer(Modifier.width(14.dp)); Column(Modifier.weight(1f)) { Text(data.group.title, fontWeight = FontWeight.SemiBold); Text("${data.count} ресурсов", color = Muted, fontSize = 12.sp) }; Column(horizontalAlignment = Alignment.End) { Text("$percentage%", color = color, fontSize = 19.sp, fontWeight = FontWeight.Bold); Text("онлайн", color = Muted, fontSize = 11.sp) } } } }

@Composable private fun ResourceRow(row: ResourceWithResult) { val result = row.result; val color = if (result == null) Muted else if (result.isOk) Good else Bad; Card(colors = CardDefaults.cardColors(CardBlue), shape = RoundedCornerShape(14.dp), modifier = Modifier.fillMaxWidth()) { Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(10.dp).clip(CircleShape).background(color)); Spacer(Modifier.width(12.dp)); Column(Modifier.weight(1f)) { Text(row.resource.name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis); Text(row.resource.url, color = Muted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis) }; Text(result?.let { if (it.isOk) "${it.responseTimeMs} мс" else it.status.title } ?: "Нет данных", color = color, fontSize = 12.sp) } } }

@Composable private fun HistoryTab(history: List<NetworkSummary>) { LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { item { Header("История") { Icon(Icons.Outlined.CalendarMonth, "Календарь", tint = Muted) } }; item { Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(CardBlue), horizontalArrangement = Arrangement.SpaceEvenly) { Text("Статистика", fontWeight = FontWeight.Bold, modifier = Modifier.padding(12.dp)); Text("Журнал", color = Muted, modifier = Modifier.padding(12.dp)) } }; item { HistorySummary(history) }; item { HistoryChart(history) }; items(history.reversed().take(20)) { h -> ListItem(headlineContent = { Text("${h.availabilityIndex}% · ${h.mode.title}") }, supportingContent = { Text(formatTime(h.lastUpdated), color = Muted) }, leadingContent = { Icon(if (h.mode == NetworkMode.NORMAL) Icons.Outlined.CheckCircle else Icons.Outlined.WarningAmber, null, tint = if (h.mode == NetworkMode.NORMAL) Good else Warn) }, colors = ListItemDefaults.colors(containerColor = Color.Transparent)) }; if (history.isEmpty()) item { EmptyCard("История появится после первой проверки", "Откройте Главную и запустите проверку") } } }
@Composable private fun HistorySummary(history: List<NetworkSummary>) { val latest = history.lastOrNull()?.availabilityIndex ?: 0; Card(colors = CardDefaults.cardColors(CardBlue), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(16.dp)) { Row(verticalAlignment = Alignment.CenterVertically) { Text("Общая доступность", fontWeight = FontWeight.SemiBold); Spacer(Modifier.weight(1f)); Text("$latest%", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = Good) }; Spacer(Modifier.height(12.dp)); LinearProgressIndicator(progress = { latest / 100f }, modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape), color = Good, trackColor = Color(0xFF294761)) } } }
@Composable private fun HistoryChart(history: List<NetworkSummary>) { Card(colors = CardDefaults.cardColors(CardBlue), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth().height(190.dp)) { Canvas(Modifier.fillMaxSize().padding(18.dp)) { if (history.size < 2) return@Canvas; val maxX = history.size - 1; history.zipWithNext().forEachIndexed { i, pair -> val x1 = size.width * i / maxX; val x2 = size.width * (i + 1) / maxX; val y1 = size.height - size.height * pair.first.availabilityIndex / 100f; val y2 = size.height - size.height * pair.second.availabilityIndex / 100f; drawLine(Cyan, Offset(x1, y1), Offset(x2, y2), 4f, cap = StrokeCap.Round) } } } }

@Composable private fun SettingsTab(vm: MainViewModel, pairing: DevicePairingState) { val settings by vm.settings.collectAsState(); val exportJson by vm.exportJson.collectAsState(); var importText by remember { mutableStateOf("") }; LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { item { Header("Настройки") }; item { SettingsSection("Основные") { SettingRow(Icons.Outlined.CalendarMonth, "Интервал автообновления", "${settings.checkIntervalSeconds} секунд"); SettingRow(Icons.Outlined.Refresh, "Автообновление", "Включено"); SettingRow(Icons.Outlined.Settings, "Тема", "Тёмная"); SettingRow(Icons.Outlined.NotificationsNone, "Уведомления", if (settings.notificationsEnabled) "Включены" else "Выключены") } }; item { SettingsSection("Связь с сайтом") { when (pairing.status) { "authorized" -> Text("Устройство подключено. Результаты синхронизируются с NetWeather.", color = Good, modifier = Modifier.padding(16.dp)); "pending" -> Column(Modifier.padding(16.dp)) { Text("Введите одноразовый код на netweather.online", color = Muted); SelectionContainer { Text(pairing.userCode ?: "—", fontSize = 28.sp, fontWeight = FontWeight.Bold, color = Cyan) }; Text("Код обновляется для каждой попытки и действует ограниченное время.", color = Muted, fontSize = 12.sp) }; "expired" -> Text("Срок действия кода истёк. Получите новый код.", color = Warn, modifier = Modifier.padding(16.dp)); else -> Text("Приложение работает локально. Подключите его к сайту для передачи состояния сети.", color = Muted, modifier = Modifier.padding(16.dp)) }; Button(onClick = vm::startPairing, enabled = pairing.status != "pending", modifier = Modifier.padding(horizontal = 16.dp).fillMaxWidth()) { Text(if (pairing.status == "authorized") "Переподключить устройство" else "Получить код подключения") } } }; item { SettingsSection("Данные") { SettingRow(Icons.Outlined.Download, "Экспорт ресурсов", "JSON"); if (exportJson.isNotBlank()) SelectionContainer { Text(exportJson, color = Muted, fontSize = 11.sp, modifier = Modifier.padding(16.dp)) }; OutlinedTextField(importText, { importText = it }, label = { Text("JSON для импорта") }, modifier = Modifier.padding(16.dp).fillMaxWidth(), minLines = 3); Button(onClick = { vm.importResources(importText); importText = "" }, enabled = importText.isNotBlank(), modifier = Modifier.padding(horizontal = 16.dp).fillMaxWidth()) { Text("Импортировать") } } }; item { SettingsSection("О приложении") { SettingRow(Icons.Outlined.Public, "NetWeather", "0.4.1 alpha") } } } }
@Composable private fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) { Column { Text(title, color = Muted, fontSize = 12.sp, modifier = Modifier.padding(horizontal = 4.dp, vertical = 4.dp)); Card(colors = CardDefaults.cardColors(CardBlue), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(content = content) } } }
@Composable private fun SettingRow(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, value: String) { Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) { Icon(icon, null, tint = Cyan, modifier = Modifier.size(22.dp)); Spacer(Modifier.width(14.dp)); Column(Modifier.weight(1f)) { Text(title, fontWeight = FontWeight.SemiBold); Text(value, color = Muted, fontSize = 12.sp) }; Text("›", color = Muted, fontSize = 24.sp) } }
@Composable private fun EmptyCard(title: String, message: String) { Card(colors = CardDefaults.cardColors(CardBlue), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(20.dp)) { Text(title, fontWeight = FontWeight.SemiBold); Text(message, color = Muted, fontSize = 13.sp) } } }
@Composable private fun AddResourceDialog(onDismiss: () -> Unit, onAdd: (String, String, ResourceGroup) -> Unit) { var name by remember { mutableStateOf("") }; var url by remember { mutableStateOf("") }; var group by remember { mutableStateOf(ResourceGroup.CUSTOM) }; AlertDialog(onDismissRequest = onDismiss, title = { Text("Добавить ресурс") }, text = { Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { OutlinedTextField(name, { name = it }, label = { Text("Название") }, singleLine = true); OutlinedTextField(url, { url = it }, label = { Text("URL или домен") }, singleLine = true); ResourceGroup.values().forEach { item -> FilterChip(selected = group == item, onClick = { group = item }, label = { Text(item.title) }) } } }, confirmButton = { Button(enabled = name.isNotBlank() && url.isNotBlank(), onClick = { onAdd(name.trim(), url.trim(), group) }) { Text("Добавить") } }, dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } }) }
fun formatTime(ts: Long): String = if (ts <= 0) "—" else SimpleDateFormat("dd.MM HH:mm:ss", Locale.getDefault()).format(Date(ts))
