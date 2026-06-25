package com.netweather.presentation.settings.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.netweather.domain.model.Resource

@Composable
fun ResourceGroupManager(
    russianResources: List<Resource>,
    internationalResources: List<Resource>,
    customResources: List<Resource>,
    onToggleResource: (Long) -> Unit,
    onDeleteResource: (Long) -> Unit,
    onAddResource: (String, String) -> Unit,
    modifier: Modifier = Modifier
) {
    var showAddDialog by remember { mutableStateOf(false) }
    
    SettingsCard(
        title = "Ресурсы для мониторинга",
        modifier = modifier
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            ResourceGroupSection(
                title = "🇷 Российские ресурсы",
                resources = russianResources,
                onToggleResource = onToggleResource,
                canDelete = false
            )
            
            ResourceGroupSection(
                title = "🌍 Международные ресурсы",
                resources = internationalResources,
                onToggleResource = onToggleResource,
                canDelete = false
            )
            
            ResourceGroupSection(
                title = "⭐ Пользовательские ресурсы",
                resources = customResources,
                onToggleResource = onToggleResource,
                onDeleteResource = onDeleteResource,
                canDelete = true
            )
            
            Button(
                onClick = { showAddDialog = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(text = "Добавить пользовательский ресурс")
            }
        }
    }
    
    if (showAddDialog) {
        AddResourceDialog(
            onDismiss = { showAddDialog = false },
            onConfirm = { name, url ->
                onAddResource(name, url)
                showAddDialog = false
            }
        )
    }
}

@Composable
private fun ResourceGroupSection(
    title: String,
    resources: List<Resource>,
    onToggleResource: (Long) -> Unit,
    onDeleteResource: ((Long) -> Unit)? = null,
    canDelete: Boolean = false
) {
    Column {
        Text(
            text = title,
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurface
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        if (resources.isEmpty()) {
            Text(
                text = "Нет ресурсов",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        } else {
            Column(
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                resources.forEach { resource ->
                    ResourceItem(
                        resource = resource,
                        onToggle = { onToggleResource(resource.id) },
                        onDelete = if (canDelete && onDeleteResource != null) {
                            { onDeleteResource(resource.id) }
                        } else null
                    )
                }
            }
        }
    }
}

@Composable
private fun ResourceItem(
    resource: Resource,
    onToggle: () -> Unit,
    onDelete: (() -> Unit)? = null
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = resource.name,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            
            Text(
                text = resource.url,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        
        Spacer(modifier = Modifier.width(8.dp))
        
        Switch(
            checked = resource.enabled,
            onCheckedChange = { onToggle() }
        )
        
        if (onDelete != null) {
            Spacer(modifier = Modifier.width(4.dp))
            
            TextButton(
                onClick = onDelete
            ) {
                Text(
                    text = "Удалить",
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}