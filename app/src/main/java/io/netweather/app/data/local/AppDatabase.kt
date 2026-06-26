package io.netweather.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters
import io.netweather.app.domain.model.*

class Converters {
    @TypeConverter fun toGroup(value: String) = ResourceGroup.valueOf(value)
    @TypeConverter fun fromGroup(value: ResourceGroup) = value.name
    @TypeConverter fun toMethod(value: String) = CheckMethod.valueOf(value)
    @TypeConverter fun fromMethod(value: CheckMethod) = value.name
    @TypeConverter fun toStatus(value: String) = DiagnosticStatus.valueOf(value)
    @TypeConverter fun fromStatus(value: DiagnosticStatus) = value.name
    @TypeConverter fun toMode(value: String) = NetworkMode.valueOf(value)
    @TypeConverter fun fromMode(value: NetworkMode) = value.name
}

@Database(entities = [ResourceEntity::class, CheckResultEntity::class, HistoryEntity::class], version = 1, exportSchema = true)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun resourceDao(): ResourceDao
    abstract fun checkResultDao(): CheckResultDao
    abstract fun historyDao(): HistoryDao
}
