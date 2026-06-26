package com.netweather.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.netweather.data.local.db.dao.CheckResultDao
import com.netweather.data.local.db.dao.HistoryDao
import com.netweather.data.local.db.dao.ResourceDao
import com.netweather.data.local.db.entity.CheckResultEntity
import com.netweather.data.local.db.entity.HistoryEntity
import com.netweather.data.local.db.entity.ResourceEntity

@Database(
    entities = [
        ResourceEntity::class,
        CheckResultEntity::class,
        HistoryEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    
    abstract fun resourceDao(): ResourceDao
    
    abstract fun checkResultDao(): CheckResultDao
    
    abstract fun historyDao(): HistoryDao
}