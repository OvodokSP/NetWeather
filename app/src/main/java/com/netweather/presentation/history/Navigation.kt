package com.netweather.presentation.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.netweather.presentation.history.HistoryScreen
import com.netweather.presentation.main.MainScreen
import com.netweather.presentation.settings.SettingsScreen

/**
 * Основная навигация приложения
 * Связывает все экраны и предоставляет нижнюю панель навигации
 */
@Composable
fun NetWeatherNavigation() {
    val navController = rememberNavController()
    
    Scaffold(
        bottomBar = {
            val navBackStackEntry by navController.currentBackStackEntryAsState()
            val currentDestination = navBackStackEntry?.destination
            
            NavigationBar {
                navigationItems.forEach { item ->
                    NavigationBarItem(
                        icon = {
                            Icon(
                                imageVector = item.icon,
                                contentDescription = item.label
                            )
                        },
                        label = { Text(item.label) },
                        selected = currentDestination?.hierarchy?.any { it.route == item.route } == true,
                        onClick = {
                            navController.navigate(item.route) {
                                // Очищаем стек до начального экрана, чтобы не накапливать экраны
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                // Избегаем дублирования при повторном нажатии на ту же вкладку
                                launchSingleTop = true
                                // Восстанавливаем состояние при возврате на вкладку
                                restoreState = true
                            }
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                            unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = NavigationRoutes.MAIN,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(NavigationRoutes.MAIN) {
                MainScreen()
            }
            
            composable(NavigationRoutes.HISTORY) {
                HistoryScreen()
            }
            
            composable(NavigationRoutes.SETTINGS) {
                SettingsScreen()
            }
        }
    }
}

/**
 * Модель элемента нижней навигации
 */
data class NavigationItem(
    val route: String,
    val icon: ImageVector,
    val label: String
)

/**
 * Список элементов навигации
 */
private val navigationItems = listOf(
    NavigationItem(
        route = NavigationRoutes.MAIN,
        icon = Icons.Default.Home,
        label = "Главная"
    ),
    NavigationItem(
        route = NavigationRoutes.HISTORY,
        icon = Icons.Default.History,
        label = "История"
    ),
    NavigationItem(
        route = NavigationRoutes.SETTINGS,
        icon = Icons.Default.Settings,
        label = "Настройки"
    )
)