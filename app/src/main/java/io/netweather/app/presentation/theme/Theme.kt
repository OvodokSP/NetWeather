package io.netweather.app.presentation.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Light = lightColorScheme(primary = Color(0xFF1565C0), secondary = Color(0xFF00897B), tertiary = Color(0xFFFFA000), background = Color(0xFFF7F9FC), surface = Color.White)
private val Dark = darkColorScheme(primary = Color(0xFF90CAF9), secondary = Color(0xFF80CBC4), tertiary = Color(0xFFFFD54F))
@Composable fun NetWeatherTheme(darkTheme: Boolean = false, content: @Composable () -> Unit) { MaterialTheme(colorScheme = if (darkTheme) Dark else Light, typography = Typography(), content = content) }
