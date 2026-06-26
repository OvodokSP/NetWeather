package io.netweather.app.di

import android.content.Context
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import io.netweather.app.data.*
import io.netweather.app.data.local.AppDatabase
import io.netweather.app.data.network.NetworkDiagnostics
import io.netweather.app.domain.logic.NetworkAnalyzer
import io.netweather.app.domain.repository.NetWeatherRepository
import io.netweather.app.notification.AppNotifier
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton fun db(@ApplicationContext context: Context): AppDatabase = Room.databaseBuilder(context, AppDatabase::class.java, "netweather.db").fallbackToDestructiveMigration().build()
    @Provides @Singleton fun diagnostics() = NetworkDiagnostics()
    @Provides @Singleton fun analyzer() = NetworkAnalyzer()
    @Provides @Singleton fun stateStore(@ApplicationContext context: Context) = StateStore(context)
    @Provides @Singleton fun notifier(@ApplicationContext context: Context) = AppNotifier(context)
    @Provides @Singleton fun repo(@ApplicationContext context: Context, db: AppDatabase, diagnostics: NetworkDiagnostics, analyzer: NetworkAnalyzer, stateStore: StateStore, notifier: AppNotifier): NetWeatherRepository = NetWeatherRepositoryImpl(context, db, diagnostics, analyzer, stateStore, notifier)
}
