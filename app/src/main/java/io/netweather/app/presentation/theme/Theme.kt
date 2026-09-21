package io.netweather.app.presentation.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val NetWeatherDark = darkColorScheme(
    primary = Color(0xFF3A8DFF), onPrimary = Color.White,
    secondary = Color(0xFF00B4DB), tertiary = Color(0xFF2ECC71),
    background = Color(0xFF061321), onBackground = Color(0xFFF4F7FB),
    surface = Color(0xFF0B1D31), onSurface = Color(0xFFF4F7FB),
    surfaceVariant = Color(0xFF122B43), onSurfaceVariant = Color(0xFFAAB9C9),
    outline = Color(0xFF294761), error = Color(0xFFE85D5D)
)

@Composable
fun NetWeatherTheme(darkTheme: Boolean = true, content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = NetWeatherDark, typography = Typography(), content = content)
}
