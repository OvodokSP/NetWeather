import unittest

from app.assessment import IncidentClassification, assess_incident
from app.diagnostics import DiagnosticPriority, QuotaManager
from app.providers import classify_globalping_http


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

    def test_globalping_internal_errors_do_not_prove_regional_outage(self):
        result = assess_incident("TIMEOUT", external_failures=4)
        self.assertEqual(result.classification, IncidentClassification.SERVICE_DOWN)
        self.assertEqual(result.confidence, "low")

    def test_globalping_confirmed_service_down_flows_to_incident(self):
        result = assess_incident("TIMEOUT", external_classification="SERVICE_DOWN")
        self.assertEqual(result.classification, IncidentClassification.SERVICE_DOWN)
        self.assertEqual(result.confidence, "high")


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


class GlobalpingClassificationTest(unittest.TestCase):
    def test_multiple_resolver_failures_are_dns_failure(self):
        payload = {"status":"finished", "results":[
            {"probe":{"country":"DE"},"result":{"status":"failed","failureSource":"resolver"}},
            {"probe":{"country":"NL"},"result":{"status":"failed","failureSource":"resolver"}},
            {"probe":{"country":"US"},"result":{"status":"failed","failureSource":"target"}},
        ]}
        result = classify_globalping_http(payload)
        self.assertEqual(result["classification"], "DNS_FAILURE")
        self.assertEqual(result["resolver_failures"], 2)

    def test_single_mixed_probe_is_not_enough_to_call_regional_outage(self):
        payload = {"status":"finished", "results":[
            {"probe":{"country":"DE"},"result":{"status":"finished","statusCode":200,"timings":{"total":120}}},
            {"probe":{"country":"RU"},"result":{"status":"failed","failureSource":"target"}},
        ]}
        result = classify_globalping_http(payload)
        self.assertEqual(result["classification"], "UNKNOWN")
        self.assertEqual(result["reachable"], 1)

    def test_repeated_failures_from_one_country_can_be_regional(self):
        payload = {"status":"finished", "results":[
            {"probe":{"country":"DE"},"result":{"status":"finished","statusCode":200}},
            {"probe":{"country":"FR"},"result":{"status":"finished","statusCode":200}},
            {"probe":{"country":"US"},"result":{"status":"finished","statusCode":200}},
            {"probe":{"country":"RU"},"result":{"status":"failed","failureSource":"target"}},
            {"probe":{"country":"RU"},"result":{"status":"failed","failureSource":"target"}},
        ]}
        result = classify_globalping_http(payload)
        self.assertEqual(result["classification"], "REGIONAL_OUTAGE")

    def test_widespread_target_failure_is_service_down(self):
        payload = {"status":"finished", "results":[
            {"probe":{"country":"DE"},"result":{"status":"failed","failureSource":"target"}},
            {"probe":{"country":"US"},"result":{"status":"failed","failureSource":"target"}},
            {"probe":{"country":"JP"},"result":{"status":"failed","failureSource":"target"}},
        ]}
        result = classify_globalping_http(payload)
        self.assertEqual(result["classification"], "SERVICE_DOWN")


if __name__ == "__main__":
    unittest.main()
