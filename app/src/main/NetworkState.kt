package com.netweather.domain.model

/**
 * Агрегированное состояние сети для отображения на главном экране
 */
data class NetworkState(
    val availabilityIndex: AvailabilityIndex,
    val networkMode: NetworkMode,
    val lastCheckTime: Long,
    val availableCount: Int,
    val unavailableCount: Int,
    val totalResources: Int,
    val resourceStates: Map<ResourceGroup, List<ResourceState>> = emptyMap(),
    val recentChanges: List<NetworkChange> = emptyList()
) {
    fun getAvailabilityPercentage(): Int {
        return if (totalResources > 0) {
            (availableCount * 100) / totalResources
        } else {
            0
        }
    }
    
    fun hasProblematicResources(): Boolean {
        return unavailableCount > 0
    }
    
    fun getProblematicCountByGroup(group: ResourceGroup): Int {
        return resourceStates[group]?.count { !it.isAvailable } ?: 0
    }
}

/**
 * Состояние отдельного ресурса
 */
data class ResourceState(
    val resource: Resource,
    val lastCheckResult: CheckResult?,
    val isAvailable: Boolean,
    val responseTimeMs: Long = 0,
    val lastCheckTime: Long = 0
) {
    fun getDiagnosticStatus(): DiagnosticStatus {
        return lastCheckResult?.getFirstErrorStatus() ?: DiagnosticStatus.UNKNOWN_ERROR
    }
    
    fun getErrorDescription(): String {
        return lastCheckResult?.getErrorDescription() ?: "Нет данных"
    }
}

/**
 * Изменение в состоянии сети
 */
data class NetworkChange(
    val timestamp: Long,
    val resourceName: String,
    val previousStatus: DiagnosticStatus,
    val currentStatus: DiagnosticStatus,
    val description: String
) {
    fun isRecovery(): Boolean {
        return previousStatus != DiagnosticStatus.OK && currentStatus == DiagnosticStatus.OK
    }
    
    fun isFailure(): Boolean {
        return previousStatus == DiagnosticStatus.OK && currentStatus != DiagnosticStatus.OK
    }
}