import importlib
import os
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class NetWeatherApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NETWEATHER_DB"] = str(Path(self.tmp.name) / "test.db")
        os.environ["NETWEATHER_API_TOKEN"] = "test-token"
        os.environ["NETWEATHER_UI_PASSWORD"] = "owner-pass"
        os.environ["NETWEATHER_AGENT_TOKEN"] = "agent-token"
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
        self.client_ctx = TestClient(self.main.app, base_url="https://testserver")
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
        self.assertEqual(payload["summary"]["mode"], "NO_DOMESTIC_PROBE")
        self.assertFalse(payload["summary"]["domestic_probe_online"])
        self.assertEqual(self.client.head("/").status_code, 200)
        self.assertEqual(self.client.get("/api/system").status_code, 200)
        self.assertEqual(self.client.get("/api/groups").status_code, 200)

    def test_owner_session_and_group_crud(self):
        status = self.client.get("/api/session")
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()["authenticated"])
        self.assertFalse(status.json()["auth_required"])

        login = self.client.post("/api/session/login", json={"password":"anything"})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["open_access"])
        self.assertTrue(self.client.get("/api/session").json()["authenticated"])

        created = self.client.post("/api/groups", json={"title":"Рабочие сервисы","key":"WORK","color":"#3A8DFF"})
        self.assertEqual(created.status_code, 200)
        groups = self.client.get("/api/groups").json()
        self.assertTrue(any(g["id"] == "WORK" and g["title"] == "Рабочие сервисы" for g in groups))

        patched = self.client.patch("/api/groups/WORK", json={"title":"Работа","color":"#2ECC71"})
        self.assertEqual(patched.status_code, 200)

        resource = self.client.post("/api/resources", json={"name":"Work test","target":"https://example.com","group_name":"WORK"})
        self.assertEqual(resource.status_code, 200)

        deleted = self.client.delete("/api/groups/WORK")
        self.assertEqual(deleted.status_code, 200)
        detail = self.client.get("/api/resources/%d" % resource.json()["id"]).json()
        self.assertEqual(detail["resource"]["group_name"], "CUSTOM")

        logout = self.client.post("/api/session/logout")
        self.assertEqual(logout.status_code, 200)
        self.assertTrue(self.client.get("/api/session").json()["authenticated"])

    def test_realtime_and_event_feed(self):
        rt = self.client.get("/api/realtime?minutes=60&scope=EXTERNAL")
        self.assertEqual(rt.status_code, 200)
        payload = rt.json()
        self.assertEqual(payload["scope"], "EXTERNAL")
        self.assertIn("resources", payload)
        self.assertEqual(len(payload["resources"]), 8)
        events = self.client.get("/api/events?limit=10")
        self.assertEqual(events.status_code, 200)
        self.assertIsInstance(events.json(), list)

    def test_realtime_uses_rolling_availability(self):
        rid = self.client.get("/api/dashboard").json()["resources"][0]["id"]
        now = int(time.time())
        with self.main.db() as conn:
            for idx in range(60):
                status = "TIMEOUT" if idx == 30 else "OK"
                conn.execute(
                    "INSERT INTO checks(resource_id,checked_at,status,response_time_ms,probe_scope) VALUES(?,?,?,?,?)",
                    (rid, now - (59 - idx) * 60, status, 120 if status == "OK" else 8000, "EXTERNAL"),
                )
        payload = self.client.get("/api/realtime?minutes=60&scope=EXTERNAL").json()
        self.assertEqual(payload["availability_window_seconds"], 3600)
        row = next(r for r in payload["resources"] if r["id"] == rid)
        self.assertTrue(row["points"])
        latest = row["points"][-1]["availability"]
        self.assertGreater(latest, 98.0)
        self.assertLess(latest, 99.0)

    def test_resource_crud_and_auth(self):
        created = self.client.post("/api/resources", json={"name":"X","target":"https://example.com","group_name":"TEST"})
        self.assertEqual(created.status_code, 200)
        rid = created.json()["id"]
        patched = self.client.patch("/api/resources/%d" % rid, headers=self.auth, json={"slow_threshold_ms":1200,"failure_threshold":3})
        self.assertEqual(patched.status_code, 200)
        detail = self.client.get("/api/resources/%d" % rid).json()
        self.assertEqual(detail["resource"]["slow_threshold_ms"], 1200)
        deleted = self.client.delete("/api/resources/%d" % rid, headers=self.auth)
        self.assertEqual(deleted.status_code, 200)

    def test_domestic_probe_classification(self):
        dash = self.client.get("/api/dashboard").json()
        rid = dash["resources"][0]["id"]
        # External result is created directly, then domestic probe reports a failure.
        good = {"status":"OK","response_time_ms":120,"dns_ms":10,"tcp_ms":20,"tls_ms":30,"http_ms":60,
                "http_status":200,"resolved_ip":"93.184.216.34","tls_days_left":90,
                "final_url":"https://example.com","location":None,"message":"HTTP 200"}
        self.main.write_check(rid, good)
        headers = {"X-NetWeather-Agent":"agent-token"}
        payload = {"resource_id":rid,"status":"TIMEOUT","response_time_ms":8000,"dns_ms":10,"tcp_ms":20,
                   "tls_ms":30,"http_ms":None,"http_status":None,"resolved_ip":"93.184.216.34","message":"timeout"}
        for _ in range(2):
            r = self.client.post("/api/agent/result?probe_key=RU_TEST&probe_name=RU%20test", headers=headers, json=payload)
            self.assertEqual(r.status_code, 200)
        dash = self.client.get("/api/dashboard").json()
        row = next(x for x in dash["resources"] if x["id"] == rid)
        self.assertEqual(row["diagnosis"], "LIKELY_RESTRICTION")
        self.assertTrue(dash["summary"]["domestic_probe_online"])
        self.assertGreaterEqual(dash["summary"]["likely_restriction"], 1)
        self.assertEqual(len(self.client.get("/api/incidents?active=true").json()), 1)

    def test_bulk_incident_acknowledgement(self):
        created = self.client.post("/api/resources", json={"name":"Bulk Ack","target":"https://example.com","failure_threshold":1})
        rid = created.json()["id"]
        bad = {"status":"TIMEOUT","response_time_ms":8000,"dns_ms":10,"tcp_ms":20,"tls_ms":30,"http_ms":None,"http_status":None,"resolved_ip":"93.184.216.34","tls_days_left":90,"final_url":"https://example.com","location":None,"message":"timeout"}
        self.main.write_check(rid, bad)
        incidents = self.client.get("/api/incidents?active=true").json()
        self.assertTrue(any(i["resource_id"] == rid and i["acknowledged_at"] is None for i in incidents))
        result = self.client.post("/api/incidents/ack-all")
        self.assertEqual(result.status_code, 200)
        self.assertGreaterEqual(result.json()["acknowledged"], 1)
        incidents = self.client.get("/api/incidents?active=true").json()
        row = next(i for i in incidents if i["resource_id"] == rid)
        self.assertIsNotNone(row["acknowledged_at"])

    def test_incident_trigger_and_recovery(self):
        created = self.client.post("/api/resources", headers=self.auth, json={"name":"Trigger","target":"https://example.com","failure_threshold":2})
        rid = created.json()["id"]
        bad = {"status":"TIMEOUT","response_time_ms":8000,"dns_ms":10,"tcp_ms":20,"tls_ms":30,"http_ms":None,"http_status":None,"resolved_ip":"93.184.216.34","tls_days_left":90,"final_url":"https://example.com","location":None,"message":"timeout"}
        self.main.write_check(rid, bad)
        self.assertEqual(len(self.client.get("/api/incidents?active=true").json()), 0)
        self.main.write_check(rid, bad)
        active = self.client.get("/api/incidents?active=true").json()
        self.assertEqual(len(active), 1)
        incident_id = active[0]["id"]
        self.assertIsNone(active[0]["acknowledged_at"])
        ack = self.client.post("/api/incidents/%d/ack" % incident_id)
        self.assertEqual(ack.status_code, 200)
        active = self.client.get("/api/incidents?active=true").json()
        self.assertIsNotNone(active[0]["acknowledged_at"])
        events = self.client.get("/api/events?limit=20").json()
        incident_event = next(e for e in events if e.get("incident_id") == incident_id)
        self.assertEqual(incident_event["acknowledged_at"], active[0]["acknowledged_at"])
        good = dict(bad, status="OK", response_time_ms=120, http_ms=60, http_status=200, message="HTTP 200")
        self.main.write_check(rid, good)
        self.assertEqual(len(self.client.get("/api/incidents?active=true").json()), 0)


if __name__ == "__main__":
    unittest.main()
