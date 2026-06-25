package com.netweather.data.local.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup

@Entity(tableName = "resources")
data class ResourceEntity(
    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "id")
    val id: Long = 0,
    
    @ColumnInfo(name = "name")
    val name: String,
    
    @ColumnInfo(name = "url")
    val url: String,
    
    @ColumnInfo(name = "group")
    val group: String,
    
    @ColumnInfo(name = "enabled")
    val enabled: Boolean = true,
    
    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
) {
    fun toDomain(): Resource {
        return Resource(
            id = id,
            name = name,
            url = url,
            group = ResourceGroup.valueOf(group),
            enabled = enabled,
            createdAt = createdAt
        )
    }
    
    companion object {
        fun fromDomain(resource: Resource): ResourceEntity {
            return ResourceEntity(
                id = resource.id,
                name = resource.name,
                url = resource.url,
                group = resource.group.name,
                enabled = resource.enabled,
                createdAt = resource.createdAt
            )
        }
    }
}