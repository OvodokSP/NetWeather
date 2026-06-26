package io.netweather.app

import io.netweather.app.domain.logic.NetworkAnalyzer
import io.netweather.app.domain.model.*
import org.junit.Assert.*
import org.junit.Test

class NetworkAnalyzerTest {
    private val analyzer = NetworkAnalyzer()
    private val resources = listOf(
        MonitoredResource(1, "RU1", "https://a.ru", ResourceGroup.RUSSIAN),
        MonitoredResource(2, "RU2", "https://b.ru", ResourceGroup.RUSSIAN),
        MonitoredResource(3, "INT1", "https://a.com", ResourceGroup.INTERNATIONAL),
        MonitoredResource(4, "INT2", "https://b.com", ResourceGroup.INTERNATIONAL),
    )
    @Test fun indexIsWeighted() {
        val results = listOf(
            CheckResult(1, DiagnosticStatus.OK, 10),
            CheckResult(2, DiagnosticStatus.OK, 10),
            CheckResult(3, DiagnosticStatus.DNS_ERROR, 0),
            CheckResult(4, DiagnosticStatus.DNS_ERROR, 0),
        )
        assertEquals(60, analyzer.calculateAvailabilityIndex(resources, results))
    }
    @Test fun restrictedModeDetected() {
        val extended = resources + MonitoredResource(5, "RU3", "https://c.ru", ResourceGroup.RUSSIAN)
        val results = listOf(CheckResult(1, DiagnosticStatus.OK, 10), CheckResult(2, DiagnosticStatus.OK, 10), CheckResult(5, DiagnosticStatus.OK, 10), CheckResult(3, DiagnosticStatus.TIMEOUT, 0), CheckResult(4, DiagnosticStatus.TIMEOUT, 0))
        assertEquals(NetworkMode.RESTRICTED_ACCESS, analyzer.determineMode(extended, results))
    }
}
