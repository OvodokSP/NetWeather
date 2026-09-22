import unittest
from unittest.mock import patch

from app.providers import GlobalpingProvider


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"id": "measurement-1", "status": "queued"}


class _Client:
    def __init__(self):
        self.payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, _url, **kwargs):
        self.payload = kwargs["json"]
        return _Response()


class GlobalpingProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_http_url_is_encoded_as_hostname_and_http_options(self):
        client = _Client()
        with patch("app.providers.httpx.AsyncClient", return_value=client):
            result = await GlobalpingProvider().submit_http("https://example.com/status?full=1", probes=3)
        self.assertEqual(result.external_id, "measurement-1")
        self.assertEqual(client.payload["target"], "example.com")
        self.assertEqual(client.payload["measurementOptions"], {
            "protocol": "HTTPS",
            "request": {"method": "GET", "path": "/status", "query": "full=1"},
        })


if __name__ == "__main__":
    unittest.main()
