package com.netweather.presentation.history.components

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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.presentation.history.HistoryStatistics
import com.netweather.presentation.theme.NetWeatherColors

@Composable
fun StatisticsCard(
    statistics: HistoryStatistics,
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
                text = "Статистика",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Средний/мин/макс индекс
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                StatValue(
                    label = "Средний",
                    value = "${statistics.averageIndex}%",
                    color = getColorForIndex(statistics.averageIndex)
                )
                
                StatValue(
                    label = "Минимум",
                    value = "${statistics.minIndex}%",
                    color = getColorForIndex(statistics.minIndex)
                )
                
                StatValue(
                    label = "Максимум",
                    value = "${statistics.maxIndex}%",
                    color = getColorForIndex(statistics.maxIndex)
                )
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            // Распределение режимов
            Text(
                text = "Распределение режимов",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            val percentages = statistics.getModePercentages()
            
            ModeDistribution(
                label = "Нормальный",
                percentage = percentages["normal"] ?: 0,
                color = NetWeatherColors.statusNormal
            )
            
            Spacer(modifier = Modifier.height(4.dp))
            
            ModeDistribution(
                label = "Частичная деградация",
                percentage = percentages["partial"] ?: 0,
                color = NetWeatherColors.statusWarning
            )
            
            Spacer(modifier = Modifier.height(4.dp))
            
            ModeDistribution(
                label = "Ограничения доступа",
                percentage = percentages["restricted"] ?: 0,
                color = NetWeatherColors.statusRestricted
            )
            
            Spacer(modifier = Modifier.height(4.dp))
            
            ModeDistribution(
                label = "Нет интернета",
                percentage = percentages["noInternet"] ?: 0,
                color = NetWeatherColors.statusError
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "Всего записей: ${statistics.totalEntries}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun StatValue(
    label: String,
    value: String,
    color: Color
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = color
        )
        
        Spacer(modifier = Modifier.height(4.dp))
        
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun ModeDistribution(
    label: String,
    percentage: Int,
    color: Color
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f)
        )
        
        Text(
            text = "$percentage%",
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
            color = color
        )
    }
}

private fun getColorForIndex(index: Int): Color {
    return when {
        index >= 80 -> NetWeatherColors.statusNormal
        index >= 70 -> NetWeatherColors.statusWarning
        index >= 30 -> NetWeatherColors.statusRestricted
        else -> NetWeatherColors.statusError
    }
}