import importlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class NetWeatherApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NETWEATHER_DB"] = str(Path(self.tmp.name) / "test.db")
        os.environ["NETWEATHER_API_TOKEN"] = "test-token"
        os.environ["NETWEATHER_SEED_DEFAULTS"] = "true"
        os.environ["NETWEATHER_SCHEDULER_ENABLED"] = "false"
        os.environ["FRONTEND_DIR"] = str(Path(__file__).resolve().parents[2] / "frontend")
        import app.config as config
        import app.database as database
        import app.incidents as incidents
        import app.monitor as monitor
        import app.main as main
        importlib.reload(config)
        importlib.reload(database)
        importlib.reload(incidents)
        importlib.reload(monitor)
        self.main = importlib.reload(main)
        self.client_ctx = TestClient(self.main.app)
        self.client = self.client_ctx.__enter__()
        self.auth = {"Authorization": "Bearer test-token"}

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        self.tmp.cleanup()

    def test_seed_dashboard_and_head(self):
        dash = self.client.get("/api/dashboard")
        self.assertEqual(dash.status_code, 200)
        payload = dash.json()
        self.assertEqual(len(payload["resources"]), 8)
        self.assertIn("RUSSIAN", payload["summary"]["groups"])
        self.assertIn(payload["summary"]["mode"], {"INITIALIZING","NORMAL","PARTIAL_DEGRADATION","NO_INTERNET","RESTRICTED_ACCESS"})
        self.assertEqual(self.client.head("/").status_code, 200)
        self.assertEqual(self.client.get("/api/system").status_code, 200)
        self.assertEqual(self.client.get("/api/groups").status_code, 200)

    def test_resource_crud_and_auth(self):
        denied = self.client.post("/api/resources", json={"name":"X","target":"https://example.com"})
        self.assertEqual(denied.status_code, 401)
        created = self.client.post("/api/resources", headers=self.auth, json={"name":"X","target":"https://example.com","group_name":"TEST"})
        self.assertEqual(created.status_code, 200)
        rid = created.json()["id"]
        patched = self.client.patch("/api/resources/%d" % rid, headers=self.auth, json={"slow_threshold_ms":1200,"failure_threshold":3})
        self.assertEqual(patched.status_code, 200)
        detail = self.client.get("/api/resources/%d" % rid).json()
        self.assertEqual(detail["resource"]["slow_threshold_ms"], 1200)
        deleted = self.client.delete("/api/resources/%d" % rid, headers=self.auth)
        self.assertEqual(deleted.status_code, 200)

    def test_incident_trigger_and_recovery(self):
        created = self.client.post("/api/resources", headers=self.auth, json={"name":"Trigger","target":"https://example.com","failure_threshold":2})
        rid = created.json()["id"]
        bad = {"status":"TIMEOUT","response_time_ms":8000,"dns_ms":10,"tcp_ms":20,"tls_ms":30,"http_ms":None,"http_status":None,"resolved_ip":"93.184.216.34","tls_days_left":90,"final_url":"https://example.com","location":None,"message":"timeout"}
        self.main.write_check(rid, bad)
        self.assertEqual(len(self.client.get("/api/incidents?active=true").json()), 0)
        self.main.write_check(rid, bad)
        active = self.client.get("/api/incidents?active=true").json()
        self.assertEqual(len(active), 1)
        good = dict(bad, status="OK", response_time_ms=120, http_ms=60, http_status=200, message="HTTP 200")
        self.main.write_check(rid, good)
        self.assertEqual(len(self.client.get("/api/incidents?active=true").json()), 0)


if __name__ == "__main__":
    unittest.main()
