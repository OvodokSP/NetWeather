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
        os.environ["NETWEATHER_ALLOW_OPEN_ACCESS"] = "true"
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
        self.database = database
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
        vk = next(r for r in payload["resources"] if r["name"] == "VK")
        self.assertEqual(vk["group_name"], "MESSENGERS")
        self.assertEqual(vk["catalog_key"], "msg-vk")
        self.assertEqual(vk["target"], "https://vk.ru")
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

    def test_required_owner_session_blocks_writes_until_login(self):
        self.main.AUTH_REQUIRED = True
        status = self.client.get("/api/session").json()
        self.assertTrue(status["auth_required"])
        self.assertFalse(status["authenticated"])
        blocked = self.client.post("/api/groups", json={"title":"Blocked"})
        self.assertEqual(blocked.status_code, 401)
        public_catalog = self.client.post("/api/resource-catalog/add", json={"resource_keys":["int-chatgpt"]})
        self.assertEqual(public_catalog.status_code, 200)
        public_resource = self.client.post("/api/resources", json={
            "name":"Public resource",
            "target":"https://public-add.example",
            "group_name":"UNTRUSTED GROUP",
            "interval_seconds":30,
            "expected_status_min":201,
            "expected_status_max":204,
            "slow_threshold_ms":100,
            "failure_threshold":1,
            "enabled":False,
            "alerts_enabled":True,
        })
        self.assertEqual(public_resource.status_code, 200)
        detail = self.client.get(f"/api/resources/{public_resource.json()['id']}").json()["resource"]
        self.assertEqual(detail["group_name"], "CUSTOM")
        self.assertEqual(detail["interval_seconds"], self.main.DEFAULT_INTERVAL)
        self.assertEqual(detail["expected_status_min"], 200)
        self.assertEqual(detail["expected_status_max"], 399)
        self.assertEqual(detail["slow_threshold_ms"], 1500)
        self.assertEqual(detail["failure_threshold"], 2)
        self.assertEqual(detail["enabled"], 1)
        self.assertEqual(detail["alerts_enabled"], 0)
        blocked_edit = self.client.patch(f"/api/resources/{public_resource.json()['id']}", json={"name":"Blocked"})
        self.assertEqual(blocked_edit.status_code, 401)
        login = self.client.post("/api/session/login", json={"password":"owner-pass"})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(self.client.get("/api/session").json()["authenticated"])
        created = self.client.post("/api/groups", json={"title":"Owner group","key":"OWNER"})
        self.assertEqual(created.status_code, 200)

    def test_public_custom_add_is_rate_limited(self):
        self.main.AUTH_REQUIRED = True
        self.main.PUBLIC_ADD_LIMIT = 2
        self.main._public_add_attempts.clear()
        for index in range(2):
            added = self.client.post("/api/resources", json={
                "name":f"Public {index}",
                "target":f"https://public-{index}.example",
            })
            self.assertEqual(added.status_code, 200)
        limited = self.client.post("/api/resources", json={
            "name":"Public limited",
            "target":"https://public-limited.example",
        })
        self.assertEqual(limited.status_code, 429)

    def test_catalog_http_rejection_is_reachable_not_an_incident(self):
        added = self.client.post("/api/resource-catalog/add", json={"resource_keys":["int-chatgpt"]}).json()
        rid = added["added"][0]["id"]
        detail = self.client.get("/api/resources/%d" % rid).json()["resource"]
        self.assertEqual(detail["allow_http_rejected"], 1)
        rejected = {"status":"HTTP_REJECTED","response_time_ms":220,"dns_ms":10,"tcp_ms":20,"tls_ms":30,
                    "http_ms":160,"http_status":403,"resolved_ip":"93.184.216.34","tls_days_left":90,
                    "final_url":"https://chatgpt.com","location":None,"message":"probe rejected"}
        self.main.write_check(rid, rejected)
        self.main.write_check(rid, rejected)
        active = self.client.get("/api/incidents?active=true").json()
        self.assertFalse(any(item["resource_id"] == rid for item in active))
        dashboard = self.client.get("/api/dashboard").json()
        row = next(item for item in dashboard["resources"] if item["id"] == rid)
        self.assertEqual(row["external"]["status"], "HTTP_REJECTED")

        ok = {**rejected, "status":"OK", "http_status":200, "message":"HTTP 200"}
        self.main.write_check(rid, ok)
        self.main.write_check(rid, rejected)
        events = self.client.get("/api/events?limit=30").json()
        self.assertFalse(any(
            item.get("resource_id") == rid and item.get("type") == "status_change"
            for item in events
        ))

    def test_catalog_migration_repairs_existing_http_rejection_telemetry(self):
        with self.main.db() as conn:
            resource = conn.execute(
                "SELECT id,name FROM resources WHERE catalog_key IS NOT NULL LIMIT 1"
            ).fetchone()
            self.assertIsNotNone(resource)
            rid = int(resource["id"])
            now = int(time.time())
            conn.execute("UPDATE resources SET allow_http_rejected=0 WHERE id=?", (rid,))
            conn.execute(
                """INSERT INTO checks(
                     resource_id,checked_at,status,response_time_ms,http_status,message,probe_scope
                   ) VALUES(?,?,?,?,?,?,?)""",
                (rid, now, "HTTP_ERROR", 220, 403, "HTTP 403, expected 200-399", "EXTERNAL"),
            )
            conn.execute(
                """INSERT INTO incidents(resource_id,kind,severity,opened_at,message)
                   VALUES(?,?,?,?,?)""",
                (rid, "DOWN", "critical", now, f"{resource['name']}: HTTP_ERROR — HTTP 403, expected 200-399"),
            )

        self.database.init_db()

        with self.main.db() as conn:
            repaired = conn.execute(
                "SELECT allow_http_rejected FROM resources WHERE id=?", (rid,)
            ).fetchone()
            latest = conn.execute(
                "SELECT status FROM checks WHERE resource_id=? ORDER BY id DESC LIMIT 1", (rid,)
            ).fetchone()
            false_incidents = conn.execute(
                "SELECT COUNT(*) FROM incidents WHERE resource_id=? AND kind='DOWN'", (rid,)
            ).fetchone()[0]
        self.assertEqual(repaired["allow_http_rejected"], 1)
        self.assertEqual(latest["status"], "HTTP_REJECTED")
        self.assertEqual(false_incidents, 0)

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

    def test_ranked_resource_catalog_and_batch_add(self):
        response = self.client.get("/api/resource-catalog")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["groups"]), 4)
        all_items = []
        for group in payload["groups"]:
            self.assertEqual(len(group["items"]), 10)
            ranks = [item["rank"] for item in group["items"]]
            self.assertEqual(ranks, list(range(1, 11)))
            all_items.extend(group["items"])
        self.assertEqual(len({item["key"] for item in all_items}), 40)
        self.assertEqual(len({item["target"] for item in all_items}), 40)
        self.assertTrue(any(item["already_added"] for item in all_items))

        add = self.client.post("/api/resource-catalog/add", json={"resource_keys":["int-chatgpt","msg-youtube"]})
        self.assertEqual(add.status_code, 200)
        self.assertEqual(len(add.json()["added"]), 2)
        again = self.client.post("/api/resource-catalog/add", json={"resource_keys":["int-chatgpt","msg-youtube"]})
        self.assertEqual(again.status_code, 200)
        self.assertEqual(len(again.json()["added"]), 0)
        self.assertEqual(len(again.json()["existing"]), 2)

    def test_manual_catalog_match_uses_catalog_resource_without_duplicate(self):
        match = self.client.get("/api/resource-catalog/match", params={"target":"https://github.com/openai"}).json()
        self.assertTrue(match["matched"])
        self.assertEqual(match["resource"]["key"], "int-github")
        self.assertTrue(match["already_added"])

        first = self.client.post("/api/resources", json={
            "name":"ручной YouTube",
            "target":"https://youtu.be/",
            "group_name":"CUSTOM",
        })
        self.assertEqual(first.status_code, 200)
        body = first.json()
        self.assertTrue(body["used_catalog"])
        self.assertTrue(body["created"])
        rid = body["id"]
        detail = self.client.get("/api/resources/%d" % rid).json()["resource"]
        self.assertEqual(detail["name"], "YouTube")
        self.assertEqual(detail["group_name"], "MESSENGERS")
        self.assertEqual(detail["catalog_key"], "msg-youtube")

        second = self.client.post("/api/resources", json={
            "name":"ещё YouTube",
            "target":"https://www.youtube.com/watch?v=test",
            "group_name":"RUSSIAN",
        })
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["already_exists"])
        self.assertEqual(second.json()["id"], rid)

    def test_target_metadata_blocks_private_targets(self):
        response = self.client.get("/api/target-meta", params={"target":"http://127.0.0.1/"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Private", response.json()["detail"])

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
