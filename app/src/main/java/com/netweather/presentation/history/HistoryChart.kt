package com.netweather.presentation.history.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.HistoryPeriod
import com.netweather.presentation.theme.NetWeatherColors
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HistoryChart(
    historyEntries: List<HistoryEntry>,
    period: HistoryPeriod,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "График доступности",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp)
            ) {
                if (historyEntries.isEmpty()) {
                    return@Canvas
                }
                
                val sortedEntries = historyEntries.sortedBy { it.timestamp }
                val width = size.width
                val height = size.height
                val padding = 40.dp.toPx()
                
                val chartWidth = width - padding * 2
                val chartHeight = height - padding * 2
                
                // Рисуем сетку
                val gridColor = NetWeatherColors.chartGrid
                for (i in 0..4) {
                    val y = padding + (chartHeight / 4) * i
                    drawLine(
                        color = gridColor,
                        start = Offset(padding, y),
                        end = Offset(width - padding, y),
                        strokeWidth = 1.dp.toPx()
                    )
                }
                
                // Рисуем линию графика
                val lineColor = NetWeatherColors.chartLine
                val fillColor = NetWeatherColors.chartFill
                
                val path = Path()
                val fillPath = Path()
                
                sortedEntries.forEachIndexed { index, entry ->
                    val x = padding + (chartWidth * index) / (sortedEntries.size - 1).coerceAtLeast(1)
                    val y = padding + chartHeight - (chartHeight * entry.availabilityIndex / 100f)
                    
                    if (index == 0) {
                        path.moveTo(x, y)
                        fillPath.moveTo(x, padding + chartHeight)
                        fillPath.lineTo(x, y)
                    } else {
                        path.lineTo(x, y)
                        fillPath.lineTo(x, y)
                    }
                    
                    if (index == sortedEntries.size - 1) {
                        fillPath.lineTo(x, padding + chartHeight)
                        fillPath.close()
                    }
                }
                
                // Заполнение под графиком
                drawPath(path = fillPath, color = fillColor)
                
                // Линия графика
                drawPath(
                    path = path,
                    color = lineColor,
                    style = Stroke(width = 2.dp.toPx())
                )
                
                // Рисуем точки
                sortedEntries.forEachIndexed { index, entry ->
                    val x = padding + (chartWidth * index) / (sortedEntries.size - 1).coerceAtLeast(1)
                    val y = padding + chartHeight - (chartHeight * entry.availabilityIndex / 100f)
                    
                    val pointColor = when {
                        entry.availabilityIndex >= 80 -> NetWeatherColors.statusNormal
                        entry.availabilityIndex >= 70 -> NetWeatherColors.statusWarning
                        entry.availabilityIndex >= 30 -> NetWeatherColors.statusRestricted
                        else -> NetWeatherColors.statusError
                    }
                    
                    drawCircle(
                        color = pointColor,
                        radius = 4.dp.toPx(),
                        center = Offset(x, y)
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            // Подписи времени
            if (historyEntries.isNotEmpty()) {
                val timeFormat = when (period) {
                    HistoryPeriod.HOUR -> SimpleDateFormat("HH:mm", Locale.getDefault())
                    HistoryPeriod.DAY -> SimpleDateFormat("HH:mm", Locale.getDefault())
                    HistoryPeriod.WEEK -> SimpleDateFormat("dd.MM", Locale.getDefault())
                }
                
                val sortedEntries = historyEntries.sortedBy { it.timestamp }
                val firstTime = timeFormat.format(Date(sortedEntries.first().timestamp))
                val lastTime = timeFormat.format(Date(sortedEntries.last().timestamp))
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = firstTime,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    
                    Text(
                        text = lastTime,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}