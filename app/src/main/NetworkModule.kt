package com.netweather.di

import com.netweather.data.remote.NetworkClient
import com.netweather.data.remote.NetworkDiagnostics
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    
    @Provides
    @Singleton
    fun provideNetworkClient(): NetworkClient {
        return NetworkClient()
    }
    
    @Provides
    @Singleton
    fun provideNetworkDiagnostics(
        networkClient: NetworkClient
    ): NetworkDiagnostics {
        return NetworkDiagnostics(networkClient)
    }
}