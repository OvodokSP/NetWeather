package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun IntervalSelector(
    currentInterval: Int,
    onIntervalSelected: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    val options = listOf(
        0 to "30 сек",
        1 to "1 мин",
        5 to "5 мин",
        15 to "15 мин"
    )

    SettingsCard(
        title = "Интервал проверки",
        modifier = modifier
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Текущий интервал: ${options.firstOrNull { it.first == currentInterval }?.second ?: "$currentInterval мин"}",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                options.forEach { (value, label) ->
                    FilterChip(
                        selected = currentInterval == value,
                        onClick = { onIntervalSelected(value) },
                        label = { Text(label) }
                    )
                }
            }

            Text(
                text = "Короткие интервалы могут сильнее расходовать батарею и зависят от ограничений Android.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
