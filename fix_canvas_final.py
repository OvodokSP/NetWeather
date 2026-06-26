#!/usr/bin/env python3
import os
import shutil

JAVA = "app/src/main/java/com/netweather"

# Принудительно удаляем старый файл
file_path = f"{JAVA}/presentation/main/components/AvailabilityIndexCard.kt"
if os.path.exists(file_path):
    os.remove(file_path)
    print(f"🗑️  Removed old file: {file_path}")

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created: {path}")

# Полностью переписываем файл БЕЗ MaterialTheme внутри Canvas
w(file_path, '''package com.netweather.presentation.main.components

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.AvailabilityIndex
import com.netweather.presentation.theme.NetWeatherColors
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun AvailabilityIndexCard(
    availabilityIndex: AvailabilityIndex,
    lastCheckTime: Long,
    modifier: Modifier = Modifier
) {
    val animatedProgress by animateFloatAsState(
        targetValue = availabilityIndex.value / 100f,
        animationSpec = tween(durationMillis = 1000),
        label = "Progress"
    )
    
    // ВСЕ цвета определяем ДО Canvas
    val statusColor = when {
        availabilityIndex.value >= 80 -> NetWeatherColors.statusNormal
        availabilityIndex.value >= 70 -> NetWeatherColors.statusWarning
        availabilityIndex.value >= 30 -> NetWeatherColors.statusRestricted
        else -> NetWeatherColors.statusError
    }
    
    val backgroundColor = Color(0xFFE0E0E0)
    val titleColor = MaterialTheme.colorScheme.onSurfaceVariant
    val bodyColor = MaterialTheme.colorScheme.onSurfaceVariant
    
    Card(
        modifier = modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Availability Index",
                style = MaterialTheme.typography.titleMedium,
                color = titleColor
            )
            
            Spacer(Modifier.height(16.dp))
            
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier.size(160.dp)
            ) {
                Canvas(modifier = Modifier.size(160.dp)) {
                    val strokeWidth = 12.dp.toPx()
                    val radius = (size.minDimension - strokeWidth) / 2
                    val topLeft = Offset(
                        (size.width - radius * 2) / 2,
                        (size.height - radius * 2) / 2
                    )
                    val arcSize = Size(radius * 2, radius * 2)
                    
                    // Фон круга
                    drawArc(
                        color = backgroundColor,
                        startAngle = -90f,
                        sweepAngle = 360f,
                        useCenter = false,
                        topLeft = topLeft,
                        size = arcSize,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                    
                    // Прогресс
                    drawArc(
                        color = statusColor,
                        startAngle = -90f,
                        sweepAngle = 360f * animatedProgress,
                        useCenter = false,
                        topLeft = topLeft,
                        size = arcSize,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                }
                
                Text(
                    text = "${availabilityIndex.value}%",
                    style = MaterialTheme.typography.displayLarge,
                    fontWeight = FontWeight.Bold,
                    color = statusColor
                )
            }
            
            Spacer(Modifier.height(16.dp))
            
            val statusText = when {
                availabilityIndex.value >= 80 -> "Excellent"
                availabilityIndex.value >= 70 -> "Good"
                availabilityIndex.value >= 30 -> "Acceptable"
                else -> "Poor"
            }
            
            Text(
                text = statusText,
                style = MaterialTheme.typography.titleLarge,
                color = statusColor,
                fontWeight = FontWeight.SemiBold
            )
            
            Spacer(Modifier.height(8.dp))
            
            val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
            Text(
                text = "Updated at ${timeFormat.format(Date(lastCheckTime))}",
                style = MaterialTheme.typography.bodySmall,
                color = bodyColor
            )
        }
    }
}
''')

print("\n" + "="*60)
print("✅✅✅ CANVAS ERROR DEFINITELY FIXED ✅✅✅")
print("="*60)
print("File rewritten without ANY MaterialTheme inside Canvas")