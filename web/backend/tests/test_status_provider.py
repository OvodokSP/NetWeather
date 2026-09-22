import unittest
from unittest.mock import patch

from app.intelligence import IodaProvider, OoniProvider, StatuspageProvider


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    def __init__(self, payload):
        self.payload = payload
        self.urls = []
        self.params = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, **kwargs):
        self.urls.append(url)
        self.params.append(kwargs.get("params", {}))
        return _Response(self.payload)


class StatuspageProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_official_statuspage_summary_normalizes_degraded_state(self):
        client = _Client({
            "page": {"updated_at": "2026-09-21T00:00:00Z"},
            "status": {"indicator": "minor", "description": "Partial service disruption"},
            "components": [{"name": "API Requests", "status": "degraded_performance"}],
            "incidents": [{"name": "API degradation"}],
            "scheduled_maintenances": [],
        })
        with patch("app.intelligence.httpx.AsyncClient", return_value=client):
            evidence = await StatuspageProvider().fetch("https://github.com")
        self.assertEqual(client.urls, ["https://www.githubstatus.com/api/v2/summary.json"])
        self.assertEqual(evidence.provider, "statuspage")
        self.assertEqual(evidence.status, "SIGNAL")
        self.assertEqual(evidence.classification, "PROVIDER_INCIDENT")
        self.assertEqual(evidence.summary["degraded_components"], ["API Requests"])
        self.assertEqual(evidence.summary["active_incidents"], 1)
        self.assertEqual(evidence.raw, {})

    async def test_unsupported_targets_do_not_make_outbound_requests(self):
        with patch("app.intelligence.httpx.AsyncClient") as client:
            evidence = await StatuspageProvider().fetch("https://attacker.example")
        self.assertIsNone(evidence)
        client.assert_not_called()

    async def test_empty_and_malformed_status_are_unknown(self):
        client = _Client({"page": {}, "status": {"indicator": "unexpected"}, "components": []})
        with patch("app.intelligence.httpx.AsyncClient", return_value=client):
            evidence = await StatuspageProvider().fetch("https://www.github.com")
        self.assertEqual(evidence.classification, "UNKNOWN")
        self.assertEqual(evidence.status, "NO_DATA")

    async def test_ooni_aggregation_classifies_confirmed_anomaly_counts(self):
        client = _Client({"result": {"measurement_count": 12, "anomaly_count": 3,
                                      "confirmed_count": 2, "failure_count": 3, "ok_count": 7}})
        with patch("app.intelligence.httpx.AsyncClient", return_value=client):
            evidence = await OoniProvider("https://api.ooni.example/api/v1", "RU").fetch("example.org")
        self.assertEqual(client.urls, ["https://api.ooni.example/api/v1/aggregation"])
        self.assertEqual(client.params[0]["probe_cc"], "RU")
        self.assertEqual(client.params[0]["test_name"], "web_connectivity")
        self.assertEqual(evidence.classification, "POSSIBLE_FILTERING")
        self.assertEqual(evidence.confidence, "high")
        self.assertEqual(evidence.raw["result"]["measurement_count"], 12)

    async def test_ooni_zero_measurements_are_unknown(self):
        client = _Client({"result": {"measurement_count": 0}})
        with patch("app.intelligence.httpx.AsyncClient", return_value=client):
            evidence = await OoniProvider("https://api.ooni.example/api/v1").fetch("example.org")
        self.assertEqual(evidence.classification, "UNKNOWN")
        self.assertEqual(evidence.status, "NO_DATA")

    async def test_ioda_only_counts_alerts_matching_configured_country(self):
        client = _Client({"data": [
            {"entityCode": "RU", "name": "RU signal"},
            {"entityCode": "US", "name": "other country"},
        ]})
        with patch("app.intelligence.httpx.AsyncClient", return_value=client):
            evidence = await IodaProvider("https://api.ioda.example/v2", "RU").fetch()
        self.assertEqual(client.urls, ["https://api.ioda.example/v2/outages/alerts"])
        self.assertEqual(client.params[0]["entityCode"], "RU")
        self.assertEqual(evidence.summary["alerts"], 1)
        self.assertEqual(evidence.classification, "REGIONAL_OUTAGE")
        self.assertEqual(evidence.confidence, "medium")

    async def test_ioda_unscoped_alerts_remain_unknown(self):
        client = _Client({"alerts": [{"name": "No entity scope"}]})
        with patch("app.intelligence.httpx.AsyncClient", return_value=client):
            evidence = await IodaProvider("https://api.ioda.example/v2", "RU").fetch()
        self.assertEqual(evidence.classification, "UNKNOWN")
        self.assertEqual(evidence.status, "UNSCOPED_DATA")


if __name__ == "__main__":
    unittest.main()
