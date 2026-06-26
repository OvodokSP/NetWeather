package io.netweather.app.domain.logic

import io.netweather.app.domain.model.*

class NetworkAnalyzer {
    fun calculateAvailabilityIndex(resources: List<MonitoredResource>, results: List<CheckResult>): Int {
        if (resources.isEmpty()) return 0
        fun ratio(group: ResourceGroup?): Double {
            val scoped = if (group == null) resources else resources.filter { it.group == group }
            if (scoped.isEmpty()) return 1.0
            val map = results.associateBy { it.resourceId }
            return scoped.count { map[it.id]?.isOk == true }.toDouble() / scoped.size.toDouble()
        }
        val internet = if (results.any { it.isOk }) 1.0 else 0.0
        val weighted = internet * 40.0 + ratio(ResourceGroup.RUSSIAN) * 20.0 + ratio(ResourceGroup.INTERNATIONAL) * 20.0 + ratio(ResourceGroup.CUSTOM) * 20.0
        return weighted.toInt().coerceIn(0, 100)
    }

    fun determineMode(resources: List<MonitoredResource>, results: List<CheckResult>): NetworkMode {
        if (resources.isEmpty()) return NetworkMode.NO_INTERNET
        val map = results.associateBy { it.resourceId }
        fun availability(group: ResourceGroup): Double {
            val scoped = resources.filter { it.group == group }
            if (scoped.isEmpty()) return 1.0
            return scoped.count { map[it.id]?.isOk == true }.toDouble() / scoped.size.toDouble()
        }
        val totalAvailability = resources.count { map[it.id]?.isOk == true }.toDouble() / resources.size.toDouble()
        val ru = availability(ResourceGroup.RUSSIAN)
        val intl = availability(ResourceGroup.INTERNATIONAL)
        return when {
            totalAvailability < 0.35 -> NetworkMode.NO_INTERNET
            intl < 0.30 && ru > 0.70 -> NetworkMode.RESTRICTED_ACCESS
            totalAvailability < 0.70 -> NetworkMode.PARTIAL_DEGRADATION
            else -> NetworkMode.NORMAL
        }
    }

    fun summarize(resources: List<MonitoredResource>, results: List<CheckResult>): NetworkSummary {
        val map = results.associateBy { it.resourceId }
        val available = resources.count { map[it.id]?.isOk == true }
        val problems = resources.filter { map[it.id]?.isOk != true }.map { it.name }
        val index = calculateAvailabilityIndex(resources, results)
        return NetworkSummary(index, determineMode(resources, results), System.currentTimeMillis(), resources.size, available, resources.size - available, problems.take(6))
    }
}
