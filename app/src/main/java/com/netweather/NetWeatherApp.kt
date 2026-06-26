package com.netweather

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.netweather.domain.repository.ResourceRepository
import com.netweather.domain.repository.SettingsRepository
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Application класс для NetWeather
 * Инициализирует Hilt, WorkManager и ресурсы по умолчанию
 */
@HiltAndroidApp
class NetWeatherApp : Application(), Configuration.Provider {
    
    @Inject
    lateinit var workerFactory: HiltWorkerFactory
    
    @Inject
    lateinit var resourceRepository: ResourceRepository
    
    @Inject
    lateinit var settingsRepository: SettingsRepository
    
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    override fun onCreate() {
        super.onCreate()
        
        // Инициализация ресурсов по умолчанию
        applicationScope.launch {
            try {
                resourceRepository.initializeDefaultResources()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
    
    /**
     * Конфигурация WorkManager для поддержки Hilt Workers
     */
    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}