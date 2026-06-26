package com.netweather.di

import com.netweather.data.repository.DiagnosticsRepositoryImpl
import com.netweather.data.repository.HistoryRepositoryImpl
import com.netweather.data.repository.ResourceRepositoryImpl
import com.netweather.data.repository.SettingsRepositoryImpl
import com.netweather.domain.repository.DiagnosticsRepository
import com.netweather.domain.repository.HistoryRepository
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    
    @Binds
    @Singleton
    abstract fun bindResourceRepository(
        impl: ResourceRepositoryImpl
    ): ResourceRepository
    
    @Binds
    @Singleton
    abstract fun bindDiagnosticsRepository(
        impl: DiagnosticsRepositoryImpl
    ): DiagnosticsRepository
    
    @Binds
    @Singleton
    abstract fun bindHistoryRepository(
        impl: HistoryRepositoryImpl
    ): HistoryRepository
    
    @Binds
    @Singleton
    abstract fun bindSettingsRepository(
        impl: SettingsRepositoryImpl
    ): SettingsRepository
}