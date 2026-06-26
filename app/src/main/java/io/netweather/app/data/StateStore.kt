package io.netweather.app.data

import android.content.Context
import io.netweather.app.domain.model.NetworkMode
import io.netweather.app.domain.model.NetworkSummary

class StateStore(context: Context) {
    private val prefs = context.getSharedPreferences("netweather_state", Context.MODE_PRIVATE)
    fun save(summary: NetworkSummary) {
        prefs.edit()
            .putInt("index", summary.availabilityIndex)
            .putString("mode", summary.mode.name)
            .putLong("lastUpdated", summary.lastUpdated)
            .putInt("total", summary.total)
            .putInt("available", summary.available)
            .putInt("problematic", summary.problematic)
            .putString("problems", summary.problemNames.joinToString("\n"))
            .apply()
    }
    fun load(): NetworkSummary? {
        val last = prefs.getLong("lastUpdated", 0L)
        if (last == 0L) return null
        val mode = runCatching { NetworkMode.valueOf(prefs.getString("mode", NetworkMode.NO_INTERNET.name)!!) }.getOrDefault(NetworkMode.NO_INTERNET)
        return NetworkSummary(prefs.getInt("index", 0), mode, last, prefs.getInt("total",0), prefs.getInt("available",0), prefs.getInt("problematic",0), prefs.getString("problems", "")!!.lines().filter { it.isNotBlank() })
    }
}
