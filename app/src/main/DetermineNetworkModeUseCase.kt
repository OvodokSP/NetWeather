package com.netweather.domain.usecase

import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.NetworkMode
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import javax.inject.Inject

/**
 * Use case для определения режима сети
 */
class DetermineNetworkModeUseCase @Inject constructor(
    private val calculateAvailabilityIndexUseCase: CalculateAvailabilityIndexUseCase
) {
    
    companion object {
        private const val NORMAL_THRESHOLD = 80
        private const val PARTIAL_DEGRADATION_THRESHOLD = 70
        private const val NO_INTERNET_THRESHOLD = 30
        private const val RESTRICTED_INTL_THRESHOLD = 30
        private const val RESTRICTED_RU_THRESHOLD = 70
    }
    
    /**
     * Определение режима сети на основе индекса доступности
     */
    suspend operator fun invoke(
        availabilityIndex: AvailabilityIndex,
        resources: List<Resource>,
        checkResults: List<CheckResult>
    ): Result<NetworkMode> {
        return try {
            val resourcesByGroup = resources.groupBy { it.group }
            val resultsMap = checkResults.associateBy { it.resourceId }
            
            val intlScore = calculateGroupScore(
                resourcesByGroup[ResourceGroup.INTL] ?: emptyList(),
                resultsMap
            )
            val ruScore = calculateGroupScore(
                resourcesByGroup[ResourceGroup.RU] ?: emptyList(),
                resultsMap
            )
            
            val mode = determineMode(
                index = availabilityIndex.value,
                intlScore = intlScore,
                ruScore = ruScore
            )
            
            Result.success(mode)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Определение режима сети с автоматическим расчётом индекса
     */
    suspend fun determineWithCalculation(
        resources: List<Resource>,
        checkResults: List<CheckResult>
    ): Result<NetworkMode> {
        return try {
            val indexResult = calculateAvailabilityIndexUseCase(resources, checkResults)
            
            if (indexResult.isFailure) {
                return Result.failure(indexResult.exceptionOrNull() ?: Exception("Ошибка расчёта индекса"))
            }
            
            val availabilityIndex = indexResult.getOrNull() 
                ?: return Result.success(NetworkMode.NO_INTERNET)
            
            invoke(availabilityIndex, resources, checkResults)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Определение режима сети только на основе индекса доступности
     */
    fun determineByIndex(availabilityIndex: AvailabilityIndex): NetworkMode {
        return when {
            availabilityIndex.value >= NORMAL_THRESHOLD -> NetworkMode.NORMAL
            availabilityIndex.value >= PARTIAL_DEGRADATION_THRESHOLD -> NetworkMode.PARTIAL_DEGRADATION
            availabilityIndex.value < NO_INTERNET_THRESHOLD -> NetworkMode.NO_INTERNET
            else -> NetworkMode.PARTIAL_DEGRADATION
        }
    }
    
    private fun calculateGroupScore(
        resources: List<Resource>,
        resultsMap: Map<Long, CheckResult>
    ): Int {
        if (resources.isEmpty()) {
            return 100
        }
        
        val availableCount = resources.count { resource ->
            val result = resultsMap[resource.id]
            result?.isSuccessful() == true
        }
        
        return (availableCount * 100) / resources.size
    }
    
    private fun determineMode(
        index: Int,
        intlScore: Int,
        ruScore: Int
    ): NetworkMode {
        if (index < NO_INTERNET_THRESHOLD) {
            return NetworkMode.NO_INTERNET
        }
        
        if (intlScore < RESTRICTED_INTL_THRESHOLD && ruScore > RESTRICTED_RU_THRESHOLD) {
            return NetworkMode.RESTRICTED_ACCESS
        }
        
        if (index >= NORMAL_THRESHOLD) {
            return NetworkMode.NORMAL
        }
        
        return NetworkMode.PARTIAL_DEGRADATION
    }
}