package com.netweather.data.local.db.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import com.netweather.domain.model.HistoryEntry
import com.netweather.domain.model.NetworkMode

@Entity(
    tableName = "history",
    indices = [
        Index(value = ["timestamp"]),
        Index(value = ["availability_index"])
    ]
)
data class HistoryEntity(
    @PrimaryKey(autoGenerate = true)
    @ColumnInfo(name = "id")
    val id: Long = 0,
    
    @ColumnInfo(name = "timestamp")
    val timestamp: Long = System.currentTimeMillis(),
    
    @ColumnInfo(name = "availability_index")
    val availabilityIndex: Int,
    
    @ColumnInfo(name = "network_mode")
    val networkMode: String,
    
    @ColumnInfo(name = "available_count")
    val availableCount: Int,
    
    @ColumnInfo(name = "unavailable_count")
    val unavailableCount: Int,
    
    @ColumnInfo(name = "details")
    val details: String = ""
) {
    fun toDomain(): HistoryEntry {
        return HistoryEntry(
            id = id,
            timestamp = timestamp,
            availabilityIndex = availabilityIndex,
            networkMode = NetworkMode.valueOf(networkMode),
            availableCount = availableCount,
            unavailableCount = unavailableCount,
            details = details
        )
    }
    
    companion object {
        fun fromDomain(historyEntry: HistoryEntry): HistoryEntity {
            return HistoryEntity(
                id = historyEntry.id,
                timestamp = historyEntry.timestamp,
                availabilityIndex = historyEntry.availabilityIndex,
                networkMode = historyEntry.networkMode.name,
                availableCount = historyEntry.availableCount,
                unavailableCount = historyEntry.unavailableCount,
                details = historyEntry.details
            )
        }
    }
}