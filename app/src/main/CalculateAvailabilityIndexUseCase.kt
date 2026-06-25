package com.netweather.domain.usecase

import com.netweather.domain.model.AvailabilityIndex
import com.netweather.domain.model.CheckResult
import com.netweather.domain.model.Resource
import com.netweather.domain.model.ResourceGroup
import javax.inject.Inject

/**
 * Use case для расчёта индекса доступности сети
 */
class CalculateAvailabilityIndexUseCase @Inject constructor(
    private val checkAllResourcesUseCase: CheckAllResourcesUseCase
) {
    
    /**
     * Расчёт индекса доступности на основе текущих результатов
     */
    suspend operator fun invoke(
        resources: List<Resource>,
        checkResults: List<CheckResult>
    ): Result<AvailabilityIndex> {
        return try {
            if (resources.isEmpty()) {
                return Result.success(AvailabilityIndex.create(0))
            }
            
            val resourcesByGroup = resources.groupBy { it.group }
            val resultsMap = checkResults.associateBy { it.resourceId }
            
            val internetScore = calculateGroupScore(resources, resultsMap)
            val ruScore = calculateGroupScore(resourcesByGroup[ResourceGroup.RU] ?: emptyList(), resultsMap)
            val intlScore = calculateGroupScore(resourcesByGroup[ResourceGroup.INTL] ?: emptyList(), resultsMap)
            val customScore = calculateGroupScore(resourcesByGroup[ResourceGroup.CUSTOM] ?: emptyList(), resultsMap)
            
            val index = calculateWeightedIndex(
                internetScore = internetScore,
                ruScore = ruScore,
                intlScore = intlScore,
                customScore = customScore,
                hasCustomResources = resourcesByGroup.containsKey(ResourceGroup.CUSTOM)
            )
            
            Result.success(AvailabilityIndex.create(index))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Расчёт процента доступности для группы ресурсов
     */
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
    
    /**
     * Расчёт взвешенного индекса доступности
     */
    private fun calculateWeightedIndex(
        internetScore: Int,
        ruScore: Int,
        intlScore: Int,
        customScore: Int,
        hasCustomResources: Boolean
    ): Int {
        val weights = if (hasCustomResources) {
            listOf(
                internetScore to AvailabilityIndex.DEFAULT_INTERNET_WEIGHT,
                ruScore to AvailabilityIndex.DEFAULT_RU_WEIGHT,
                intlScore to AvailabilityIndex.DEFAULT_INTL_WEIGHT,
                customScore to AvailabilityIndex.DEFAULT_CUSTOM_WEIGHT
            )
        } else {
            listOf(
                internetScore to 50,
                ruScore to 25,
                intlScore to 25
            )
        }
        
        val weightedSum = weights.sumOf { (score, weight) ->
            score * weight
        }
        
        val totalWeight = weights.sumOf { it.second }
        
        return if (totalWeight > 0) {
            weightedSum / totalWeight
        } else {
            0
        }
    }
}