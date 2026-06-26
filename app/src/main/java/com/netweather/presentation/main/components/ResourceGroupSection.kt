package com.netweather.presentation.main.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.ResourceGroup
import com.netweather.domain.model.ResourceState

@Composable
fun ResourceGroupSection(
    group: ResourceGroup,
    resources: List<ResourceState>,
    onToggleResource: (Long) -> Unit,
    modifier: Modifier = Modifier
) {
    val groupTitle = when (group) {
        ResourceGroup.RU -> "🇷🇺 Российские ресурсы"
        ResourceGroup.INTL -> "🌍 Международные ресурсы"
        ResourceGroup.CUSTOM -> "⭐ Пользовательские ресурсы"
    }
    
    val availableCount = resources.count { it.isAvailable }
    val totalCount = resources.size
    
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Column {
                Text(
                    text = groupTitle,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                
                Spacer(modifier = Modifier.height(4.dp))
                
                Text(
                    text = "Доступно: $availableCount из $totalCount",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                resources.forEach { resourceState ->
                    ResourceItem(
                        resourceState = resourceState,
                        onToggle = { onToggleResource(resourceState.resource.id) }
                    )
                }
            }
        }
    }
}