package com.netweather.presentation.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.unit.dp

val NetWeatherShapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(8.dp),
    medium = RoundedCornerShape(12.dp),
    large = RoundedCornerShape(16.dp),
    extraLarge = RoundedCornerShape(24.dp)
)

object CardShapes {
    val indexCard = RoundedCornerShape(20.dp)
    val modeCard = RoundedCornerShape(16.dp)
    val resourceCard = RoundedCornerShape(12.dp)
    val historyCard = RoundedCornerShape(12.dp)
    val settingsCard = RoundedCornerShape(12.dp)
}

object WidgetShapes {
    val smallWidget = RoundedCornerShape(16.dp)
    val mediumWidget = RoundedCornerShape(16.dp)
    val largeWidget = RoundedCornerShape(20.dp)
}

object IndicatorShapes {
    val statusDot = RoundedCornerShape(50)
    val progressBar = RoundedCornerShape(4.dp)
    val chip = RoundedCornerShape(8.dp)
}