package com.netweather.presentation.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.ThemeMode

private val LightColorScheme = lightColorScheme(
    primary = NetWeatherColors.md_theme_light_primary,
    onPrimary = NetWeatherColors.md_theme_light_onPrimary,
    primaryContainer = NetWeatherColors.md_theme_light_primaryContainer,
    onPrimaryContainer = NetWeatherColors.md_theme_light_onPrimaryContainer,
    secondary = NetWeatherColors.md_theme_light_secondary,
    onSecondary = NetWeatherColors.md_theme_light_onSecondary,
    secondaryContainer = NetWeatherColors.md_theme_light_secondaryContainer,
    onSecondaryContainer = NetWeatherColors.md_theme_light_onSecondaryContainer,
    tertiary = NetWeatherColors.md_theme_light_tertiary,
    onTertiary = NetWeatherColors.md_theme_light_onTertiary,
    tertiaryContainer = NetWeatherColors.md_theme_light_tertiaryContainer,
    onTertiaryContainer = NetWeatherColors.md_theme_light_onTertiaryContainer,
    error = NetWeatherColors.md_theme_light_error,
    errorContainer = NetWeatherColors.md_theme_light_errorContainer,
    onError = NetWeatherColors.md_theme_light_onError,
    onErrorContainer = NetWeatherColors.md_theme_light_onErrorContainer,
    background = NetWeatherColors.md_theme_light_background,
    onBackground = NetWeatherColors.md_theme_light_onBackground,
    surface = NetWeatherColors.md_theme_light_surface,
    onSurface = NetWeatherColors.md_theme_light_onSurface,
    surfaceVariant = NetWeatherColors.md_theme_light_surfaceVariant,
    onSurfaceVariant = NetWeatherColors.md_theme_light_onSurfaceVariant,
    outline = NetWeatherColors.md_theme_light_outline,
    outlineVariant = NetWeatherColors.md_theme_light_outlineVariant,
    inverseSurface = NetWeatherColors.md_theme_light_inverseSurface,
    inverseOnSurface = NetWeatherColors.md_theme_light_inverseOnSurface,
    inversePrimary = NetWeatherColors.md_theme_light_inversePrimary,
    surfaceTint = NetWeatherColors.md_theme_light_surfaceTint,
    scrim = NetWeatherColors.md_theme_light_scrim
)

private val DarkColorScheme = darkColorScheme(
    primary = NetWeatherColors.md_theme_dark_primary,
    onPrimary = NetWeatherColors.md_theme_dark_onPrimary,
    primaryContainer = NetWeatherColors.md_theme_dark_primaryContainer,
    onPrimaryContainer = NetWeatherColors.md_theme_dark_onPrimaryContainer,
    secondary = NetWeatherColors.md_theme_dark_secondary,
    onSecondary = NetWeatherColors.md_theme_dark_onSecondary,
    secondaryContainer = NetWeatherColors.md_theme_dark_secondaryContainer,
    onSecondaryContainer = NetWeatherColors.md_theme_dark_onSecondaryContainer,
    tertiary = NetWeatherColors.md_theme_dark_tertiary,
    onTertiary = NetWeatherColors.md_theme_dark_onTertiary,
    tertiaryContainer = NetWeatherColors.md_theme_dark_tertiaryContainer,
    onTertiaryContainer = NetWeatherColors.md_theme_dark_onTertiaryContainer,
    error = NetWeatherColors.md_theme_dark_error,
    errorContainer = NetWeatherColors.md_theme_dark_errorContainer,
    onError = NetWeatherColors.md_theme_dark_onError,
    onErrorContainer = NetWeatherColors.md_theme_dark_onErrorContainer,
    background = NetWeatherColors.md_theme_dark_background,
    onBackground = NetWeatherColors.md_theme_dark_onBackground,
    surface = NetWeatherColors.md_theme_dark_surface,
    onSurface = NetWeatherColors.md_theme_dark_onSurface,
    surfaceVariant = NetWeatherColors.md_theme_dark_surfaceVariant,
    onSurfaceVariant = NetWeatherColors.md_theme_dark_onSurfaceVariant,
    outline = NetWeatherColors.md_theme_dark_outline,
    outlineVariant = NetWeatherColors.md_theme_dark_outlineVariant,
    inverseSurface = NetWeatherColors.md_theme_dark_inverseSurface,
    inverseOnSurface = NetWeatherColors.md_theme_dark_inverseOnSurface,
    inversePrimary = NetWeatherColors.md_theme_dark_inversePrimary,
    surfaceTint = NetWeatherColors.md_theme_dark_surfaceTint,
    scrim = NetWeatherColors.md_theme_dark_scrim
)

@Composable
fun NetWeatherTheme(
    themeMode: ThemeMode = ThemeMode.SYSTEM,
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val darkTheme = when (themeMode) {
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
    }
    
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) 
            else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.surface.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }
    
    MaterialTheme(
        colorScheme = colorScheme,
        typography = NetWeatherTypography,
        content = content
    )
}

@Composable
fun NetworkMode.getStatusColor(): androidx.compose.ui.graphics.Color {
    return when (this) {
        NetworkMode.NORMAL -> NetWeatherColors.statusNormal
        NetworkMode.PARTIAL_DEGRADATION -> NetWeatherColors.statusWarning
        NetworkMode.RESTRICTED_ACCESS -> NetWeatherColors.statusRestricted
        NetworkMode.NO_INTERNET -> NetWeatherColors.statusError
    }
}

@Composable
fun NetworkMode.getStatusBackgroundColor(): androidx.compose.ui.graphics.Color {
    return when (this) {
        NetworkMode.NORMAL -> NetWeatherColors.statusNormalLight
        NetworkMode.PARTIAL_DEGRADATION -> NetWeatherColors.statusWarningLight
        NetworkMode.RESTRICTED_ACCESS -> NetWeatherColors.statusRestrictedLight
        NetworkMode.NO_INTERNET -> NetWeatherColors.statusErrorLight
    }
}

@Composable
fun com.netweather.domain.model.DiagnosticStatus.getStatusColor(): androidx.compose.ui.graphics.Color {
    return when (this) {
        com.netweather.domain.model.DiagnosticStatus.OK -> NetWeatherColors.resourceAvailable
        com.netweather.domain.model.DiagnosticStatus.TIMEOUT -> NetWeatherColors.resourceSlow
        com.netweather.domain.model.DiagnosticStatus.UNKNOWN_ERROR -> NetWeatherColors.statusUnknown
        else -> NetWeatherColors.resourceUnavailable
    }
}