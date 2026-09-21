import unittest
from unittest.mock import patch

from app.intelligence import StatuspageProvider


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

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url):
        self.urls.append(url)
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


if __name__ == "__main__":
    unittest.main()
