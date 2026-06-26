package io.netweather.app.presentation

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import io.netweather.app.domain.model.*
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScreen(vm: MainViewModel = hiltViewModel()) {
    val summary by vm.summary.collectAsState()
    val loading by vm.loading.collectAsState()
    val error by vm.error.collectAsState()
    val resources by vm.resources.collectAsState()
    val history by vm.historyDay.collectAsState()
    var tab by remember { mutableIntStateOf(0) }
    var showAdd by remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(error) { error?.let { snackbar.showSnackbar(it); vm.clearError() } }
    Scaffold(
        topBar = { TopAppBar(title = { Text("NetWeather") }, actions = { IconButton(onClick = vm::refreshNow) { Icon(Icons.Default.Refresh, "Обновить") } }) },
        floatingActionButton = { if (tab == 0) FloatingActionButton(onClick = { showAdd = true }) { Icon(Icons.Default.Add, "Добавить") } },
        snackbarHost = { SnackbarHost(snackbar) }
    ) { pad ->
        Column(Modifier.padding(pad).fillMaxSize()) {
            TabRow(selectedTabIndex = tab) {
                listOf("Главная", "История", "Настройки").forEachIndexed { i, t -> Tab(selected = tab == i, onClick = { tab = i }, text = { Text(t) }) }
            }
            when(tab) {
                0 -> MainTab(summary, resources, loading, vm)
                1 -> HistoryTab(history)
                2 -> SettingsTab(vm)
            }
        }
    }
    if (showAdd) AddResourceDialog(onDismiss = { showAdd = false }, onAdd = { name, url, group -> vm.addResource(name, url, group); showAdd = false })
}

@Composable fun MainTab(summary: NetworkSummary, resources: List<ResourceWithResult>, loading: Boolean, vm: MainViewModel) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { SummaryCard(summary, loading, vm::refreshNow) }
        items(resources) { row -> ResourceRow(row, onToggle = { vm.toggle(row.resource.id, it) }, onDelete = { vm.delete(row.resource) }) }
    }
}

@Composable fun SummaryCard(summary: NetworkSummary, loading: Boolean, onRefresh: () -> Unit) {
    val color = when(summary.mode) { NetworkMode.NORMAL -> Color(0xFF2E7D32); NetworkMode.PARTIAL_DEGRADATION -> Color(0xFFF9A825); NetworkMode.RESTRICTED_ACCESS -> Color(0xFFEF6C00); NetworkMode.NO_INTERNET -> Color(0xFFC62828) }
    ElevatedCard(Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text("${summary.availabilityIndex}%", style = MaterialTheme.typography.displayMedium, fontWeight = FontWeight.Bold, color = color)
        Text("Доступность сети")
        Spacer(Modifier.height(8.dp))
        Text("${summary.mode.emoji} ${summary.mode.title}", fontWeight = FontWeight.SemiBold)
        if (summary.mode == NetworkMode.RESTRICTED_ACCESS) Text("Вероятны ограничения доступа к части зарубежных ресурсов.", color = color)
        Text("Доступно: ${summary.available} | Проблем: ${summary.problematic} | Всего: ${summary.total}")
        Text("Проверено: ${formatTime(summary.lastUpdated)}", style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.height(8.dp))
        Button(onClick = onRefresh, enabled = !loading) { Text(if (loading) "Проверка…" else "Обновить") }
    } }
}

@Composable fun ResourceRow(row: ResourceWithResult, onToggle: (Boolean)->Unit, onDelete: ()->Unit) {
    val r = row.resource; val res = row.result
    ElevatedCard(Modifier.fillMaxWidth()) { Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text("${if (res?.isOk == true) "🟢" else if (res == null) "⚪" else "🔴"} ${r.name}", fontWeight = FontWeight.SemiBold)
            Text("${r.url} • ${r.group.title} • ${r.method.title}", style = MaterialTheme.typography.bodySmall)
            Text("${res?.status?.title ?: "Нет данных"} ${res?.responseTimeMs?.let { "— ${it} мс" } ?: ""}", style = MaterialTheme.typography.bodySmall)
            Text("Последний успех: ${formatTime(res?.lastSuccessfulCheck ?: 0)}", style = MaterialTheme.typography.bodySmall)
        }
        Switch(checked = r.enabled, onCheckedChange = onToggle)
        TextButton(onClick = onDelete) { Text("Удалить") }
    } }
}

@Composable fun HistoryTab(history: List<NetworkSummary>) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("История за сутки", style = MaterialTheme.typography.titleLarge) }
        item { HistoryChart(history) }
        items(history.reversed()) { h -> Text("${formatTime(h.lastUpdated)} — ${h.availabilityIndex}% — ${h.mode.title}") }
    }
}
@Composable fun HistoryChart(history: List<NetworkSummary>) { ElevatedCard(Modifier.fillMaxWidth().height(220.dp)) { Canvas(Modifier.fillMaxSize().padding(16.dp)) { if (history.size < 2) return@Canvas; val maxX = history.size - 1; history.zipWithNext().forEachIndexed { i, pair -> val x1 = size.width * i / maxX; val x2 = size.width * (i+1) / maxX; val y1 = size.height - size.height * pair.first.availabilityIndex / 100f; val y2 = size.height - size.height * pair.second.availabilityIndex / 100f; drawLine(Color(0xFF1565C0), androidx.compose.ui.geometry.Offset(x1,y1), androidx.compose.ui.geometry.Offset(x2,y2), 5f) } } } }

@Composable fun SettingsTab(vm: MainViewModel) {
    val settings by vm.settings.collectAsState()
    val exportJson by vm.exportJson.collectAsState()
    var importText by remember { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("Настройки", style = MaterialTheme.typography.titleLarge) }
        item { Text("Интервал проверки") }
        item { Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf(30 to "30 секунд", 60 to "1 минута", 300 to "5 минут", 900 to "15 минут").forEach { (sec, label) -> FilterChip(selected = settings.checkIntervalSeconds == sec, onClick = { vm.setInterval(sec) }, label = { Text(label) }) } } }
        item { Text("Короткие интервалы используют цепочку OneTimeWorkRequest и могут сильнее расходовать батарею.") }
        item { Divider() }
        item { Text("Экспорт и импорт ресурсов", style = MaterialTheme.typography.titleMedium) }
        item { Button(onClick = { vm.exportResources() }) { Text("Экспорт JSON") } }
        if (exportJson.isNotBlank()) item { SelectionContainer { Text(exportJson, style = MaterialTheme.typography.bodySmall) } }
        item { OutlinedTextField(value = importText, onValueChange = { importText = it }, label = { Text("JSON для импорта") }, modifier = Modifier.fillMaxWidth(), minLines = 3) }
        item { Button(onClick = { vm.importResources(importText); importText = "" }, enabled = importText.isNotBlank()) { Text("Импорт JSON") } }
    }
}

@Composable fun AddResourceDialog(onDismiss:()->Unit, onAdd:(String,String,ResourceGroup)->Unit) { var name by remember { mutableStateOf("") }; var url by remember { mutableStateOf("") }; var group by remember { mutableStateOf(ResourceGroup.CUSTOM) }; AlertDialog(onDismissRequest = onDismiss, title = { Text("Добавить ресурс") }, text = { Column { OutlinedTextField(name,{name=it}, label={Text("Название")}); OutlinedTextField(url,{url=it}, label={Text("URL")}); ResourceGroup.values().forEach { FilterChip(selected=group==it,onClick={group=it},label={Text(it.title)}) } } }, confirmButton = { Button(enabled = name.isNotBlank() && url.isNotBlank(), onClick = { onAdd(name,url,group) }) { Text("Добавить") } }, dismissButton = { TextButton(onClick=onDismiss){Text("Отмена")} }) }

fun formatTime(ts: Long): String = if (ts <= 0) "—" else SimpleDateFormat("dd.MM HH:mm:ss", Locale.getDefault()).format(Date(ts))
