package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
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
    SettingsCard(
        title = "Интервал проверки",
        modifier = modifier
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Каждые $currentInterval минут",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            Slider(
                value = currentInterval.toFloat(),
                onValueChange = { value ->
                    onIntervalSelected(value.toInt())
                },
                valueRange = 5f..60f,
                steps = 10
            )
            
            Text(
                text = "От 5 до 60 минут. Чем чаще проверка, тем больше расход батареи.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}