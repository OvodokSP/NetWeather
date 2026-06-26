package com.netweather.presentation.main

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.netweather.domain.model.ResourceGroup
import com.netweather.presentation.main.components.AvailabilityIndexCard
import com.netweather.presentation.main.components.NetworkModeCard
import com.netweather.presentation.main.components.ResourceGroupSection
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    viewModel: MainViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    
    LaunchedEffect(uiState.error) {
        uiState.error?.let { error ->
            snackbarHostState.showSnackbar(
                message = error,
                actionLabel = "OK"
            )
            viewModel.clearError()
        }
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "NetWeather",
                        style = MaterialTheme.typography.headlineMedium
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            if (uiState.hasData()) {
                MainContent(
                    uiState = uiState,
                    onRefresh = { viewModel.refreshData() },
                    onToggleResource = { resourceId ->
                        viewModel.toggleResource(resourceId)
                    }
                )
            } else if (!uiState.isLoading) {
                EmptyState(onRefresh = { viewModel.refreshData() })
            }
        }
    }
}

@Composable
private fun MainContent(
    uiState: MainUiState,
    onRefresh: () -> Unit,
    onToggleResource: (Long) -> Unit
) {
    val networkState = uiState.networkState ?: return
    
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Button(onClick = onRefresh, modifier = Modifier.fillMaxWidth()) {
                Text(text = "Обновить")
            }
        }

        item {
            AvailabilityIndexCard(
                availabilityIndex = networkState.availabilityIndex,
                lastCheckTime = networkState.lastCheckTime
            )
        }
        
        item {
            NetworkModeCard(
                networkMode = networkState.networkMode,
                availableCount = networkState.availableCount,
                unavailableCount = networkState.unavailableCount,
                totalResources = networkState.totalResources
            )
        }
        
        item {
            LastCheckInfo(
                lastCheckTime = networkState.lastCheckTime,
                availableCount = networkState.availableCount,
                unavailableCount = networkState.unavailableCount
            )
        }
        
        networkState.resourceStates[ResourceGroup.RU]?.let { resources ->
            if (resources.isNotEmpty()) {
                item {
                    ResourceGroupSection(
                        group = ResourceGroup.RU,
                        resources = resources,
                        onToggleResource = onToggleResource
                    )
                }
            }
        }
        
        networkState.resourceStates[ResourceGroup.INTL]?.let { resources ->
            if (resources.isNotEmpty()) {
                item {
                    ResourceGroupSection(
                        group = ResourceGroup.INTL,
                        resources = resources,
                        onToggleResource = onToggleResource
                    )
                }
            }
        }
        
        networkState.resourceStates[ResourceGroup.CUSTOM]?.let { resources ->
            if (resources.isNotEmpty()) {
                item {
                    ResourceGroupSection(
                        group = ResourceGroup.CUSTOM,
                        resources = resources,
                        onToggleResource = onToggleResource
                    )
                }
            }
        }
        
        item {
            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun LastCheckInfo(
    lastCheckTime: Long,
    availableCount: Int,
    unavailableCount: Int
) {
    val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    val timeString = timeFormat.format(Date(lastCheckTime))
    
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Последняя проверка: $timeString",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(4.dp))
        
        Text(
            text = "Доступно: $availableCount | Недоступно: $unavailableCount",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun EmptyState(onRefresh: () -> Unit) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "🌐",
                style = MaterialTheme.typography.displayLarge
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(
                text = "Нет данных",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.onSurface
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "Нажмите кнопку для первой проверки",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(onClick = onRefresh) {
                Text(text = "Обновить")
            }
        }
    }
}