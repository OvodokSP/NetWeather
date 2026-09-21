import unittest

from app.assessment import IncidentClassification, assess_incident
from app.diagnostics import DiagnosticPriority, QuotaManager


class IncidentAssessmentTest(unittest.TestCase):
    def test_global_only_is_honest(self):
        result = assess_incident("OK")
        self.assertEqual(result.classification, IncidentClassification.OK)
        self.assertEqual(result.confidence, "global")

    def test_local_failure_is_not_called_service_outage(self):
        result = assess_incident("OK", "TIMEOUT")
        self.assertEqual(result.classification, IncidentClassification.LOCAL_NETWORK)

    def test_dns_failure_is_deterministic(self):
        result = assess_incident("DNS_ERROR", "DNS_ERROR")
        self.assertEqual(result.classification, IncidentClassification.DNS_FAILURE)

    def test_possible_filtering_requires_external_signal(self):
        plain = assess_incident("OK", "TIMEOUT")
        signalled = assess_incident("OK", "TIMEOUT", ooni_signal=True)
        self.assertEqual(plain.classification, IncidentClassification.LOCAL_NETWORK)
        self.assertEqual(signalled.classification, IncidentClassification.POSSIBLE_FILTERING)


class QuotaManagerTest(unittest.TestCase):
    def test_background_cannot_spend_protected_reserve(self):
        quota = QuotaManager(hourly_limit=10, reserve_percent=30)
        self.assertTrue(quota.consume(DiagnosticPriority.BACKGROUND, 7, now=100).allowed)
        denied = quota.consume(DiagnosticPriority.BACKGROUND, 1, now=101)
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.reason, "reserve_protected")
        self.assertTrue(quota.consume(DiagnosticPriority.NEW_DOWN, 3, now=102).allowed)

    def test_old_usage_expires(self):
        quota = QuotaManager(hourly_limit=3, reserve_percent=0)
        self.assertTrue(quota.consume(DiagnosticPriority.MANUAL, 3, now=100).allowed)
        self.assertFalse(quota.consume(DiagnosticPriority.MANUAL, 1, now=101).allowed)
        self.assertTrue(quota.consume(DiagnosticPriority.MANUAL, 1, now=3701).allowed)


if __name__ == "__main__":
    unittest.main()
