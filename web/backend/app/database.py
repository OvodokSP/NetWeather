from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from .config import CLIENT_PROBE_STALE_SECONDS, DB_PATH, DEFAULT_INTERVAL, DEFAULT_RESOURCES, SEED_DEFAULTS, SERVER_PROBE_KEY, SERVER_PROBE_NAME
from .resource_catalog import CATALOG_BY_KEY, catalog_match
from .availability import is_reachable
from .assessment import assess_incident


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db() -> None:
    with db() as conn:
        conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS resources (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, target TEXT NOT NULL,
          group_name TEXT NOT NULL DEFAULT 'CUSTOM', interval_seconds INTEGER NOT NULL DEFAULT 60,
          enabled INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
          last_checked_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS checks (
          id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER NOT NULL, checked_at INTEGER NOT NULL,
          status TEXT NOT NULL, response_time_ms INTEGER NOT NULL, dns_ms INTEGER, tcp_ms INTEGER,
          tls_ms INTEGER, http_ms INTEGER, http_status INTEGER, resolved_ip TEXT, message TEXT,
          FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_checks_resource_time ON checks(resource_id, checked_at DESC);
        CREATE TABLE IF NOT EXISTS incidents (
          id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER NOT NULL, kind TEXT NOT NULL,
          severity TEXT NOT NULL, opened_at INTEGER NOT NULL, closed_at INTEGER, acknowledged_at INTEGER,
          message TEXT NOT NULL, FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_resource_open ON incidents(resource_id, closed_at, opened_at DESC);
        CREATE TABLE IF NOT EXISTS resource_groups (
          group_key TEXT PRIMARY KEY, title TEXT NOT NULL, color TEXT NOT NULL DEFAULT '#3A8DFF',
          sort_order INTEGER NOT NULL DEFAULT 100, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS probes (
          probe_key TEXT PRIMARY KEY, name TEXT NOT NULL, scope TEXT NOT NULL,
          last_seen_at INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS probe_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT, probe_key TEXT NOT NULL, resource_id INTEGER NOT NULL,
          task_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
          created_at INTEGER NOT NULL, started_at INTEGER, completed_at INTEGER, result_text TEXT,
          FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_probe_tasks_pending ON probe_tasks(probe_key,status,created_at);
        CREATE TABLE IF NOT EXISTS diagnostic_jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER NOT NULL,
          provider TEXT NOT NULL, external_id TEXT, priority INTEGER NOT NULL,
          status TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
          error TEXT, FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_diagnostic_jobs_resource ON diagnostic_jobs(resource_id,created_at DESC);
        CREATE TABLE IF NOT EXISTS provider_quota_uses (
          id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL, used_at INTEGER NOT NULL,
          cost INTEGER NOT NULL, priority INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_provider_quota_time ON provider_quota_uses(provider,used_at);
        CREATE TABLE IF NOT EXISTS external_evidence (
          id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER,
          provider TEXT NOT NULL, scope_key TEXT NOT NULL, status TEXT NOT NULL,
          classification TEXT, confidence TEXT, summary_json TEXT NOT NULL DEFAULT '{}',
          raw_json TEXT NOT NULL DEFAULT '{}', fetched_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
          FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_external_evidence_lookup
          ON external_evidence(provider,scope_key,expires_at DESC);
        CREATE TABLE IF NOT EXISTS devices (
          device_id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT,
          app_version TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'PENDING',
          created_at INTEGER NOT NULL, approved_at INTEGER, last_seen_at INTEGER NOT NULL DEFAULT 0,
          revoked_at INTEGER, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS device_authorizations (
          session_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, user_code_hash TEXT NOT NULL,
          poll_secret_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
          created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, approved_at INTEGER,
          delivered_at INTEGER, FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_device_auth_code
          ON device_authorizations(user_code_hash) WHERE status='PENDING';
        """)
        for table, name, ddl in [
            ("resources","expected_status_min","INTEGER NOT NULL DEFAULT 200"),
            ("resources","expected_status_max","INTEGER NOT NULL DEFAULT 399"),
            ("resources","slow_threshold_ms","INTEGER NOT NULL DEFAULT 1500"),
            ("resources","failure_threshold","INTEGER NOT NULL DEFAULT 2"),
            ("resources","alerts_enabled","INTEGER NOT NULL DEFAULT 1"),
            ("resources","last_success_at","INTEGER NOT NULL DEFAULT 0"),
            ("resources","last_failure_at","INTEGER NOT NULL DEFAULT 0"),
            ("resources","catalog_key","TEXT"),
            ("resources","allow_http_rejected","INTEGER NOT NULL DEFAULT 0"),
            ("checks","tls_days_left","INTEGER"),
            ("checks","final_url","TEXT"),
            ("checks","location","TEXT"),
            ("checks","probe_key","TEXT NOT NULL DEFAULT 'VPS_EU'"),
            ("checks","probe_scope","TEXT NOT NULL DEFAULT 'GLOBAL'"),
            ("probes","agent_version","TEXT NOT NULL DEFAULT ''"),
            ("probes","capabilities","TEXT NOT NULL DEFAULT ''"),
            ("diagnostic_jobs","classification","TEXT"),
            ("diagnostic_jobs","confidence","TEXT"),
            ("diagnostic_jobs","result_summary_json","TEXT NOT NULL DEFAULT '{}'"),
            ("diagnostic_jobs","raw_json","TEXT NOT NULL DEFAULT '{}'"),
            ("diagnostic_jobs","completed_at","INTEGER"),
            ("diagnostic_jobs","poll_attempts","INTEGER NOT NULL DEFAULT 0"),
            ("diagnostic_jobs","next_poll_at","INTEGER"),
            ("devices","token_expires_at","INTEGER"),
        ]:
            _ensure_column(conn, table, name, ddl)
        conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_resources_catalog_key
          ON resources(catalog_key) WHERE catalog_key IS NOT NULL AND catalog_key <> ''""")
        # Backfill catalog identity for existing resources when the target uniquely matches the curated catalog.
        for row in conn.execute("SELECT id,target,catalog_key FROM resources").fetchall():
            match = (
                CATALOG_BY_KEY.get(row["catalog_key"])
                if row["catalog_key"]
                else catalog_match(row["target"])
            )
            if match:
                try:
                    conn.execute(
                        "UPDATE resources SET catalog_key=?,target=?,group_name=?,allow_http_rejected=1 WHERE id=?",
                        (match.key, match.target, match.group_key, row["id"]),
                    )
                except sqlite3.IntegrityError:
                    pass
        # Older databases can already have catalog_key while the new flag still has its
        # column default (0). Repair both the flag and telemetry produced by anti-bot
        # responses before this migration, so a reachable catalog service is not shown
        # as a historical outage after an upgrade.
        conn.execute("""UPDATE checks
          SET status='HTTP_REJECTED',
              message='HTTP ' || http_status || ': сервис доступен, но отклонил автоматическую проверку'
          WHERE status='HTTP_ERROR' AND http_status IN (401,403,405,429)
            AND resource_id IN (SELECT id FROM resources WHERE allow_http_rejected=1)""")
        conn.execute("""DELETE FROM incidents
          WHERE kind='DOWN'
            AND resource_id IN (SELECT id FROM resources WHERE allow_http_rejected=1)
            AND (message LIKE '%HTTP_ERROR%HTTP 401%'
              OR message LIKE '%HTTP_ERROR%HTTP 403%'
              OR message LIKE '%HTTP_ERROR%HTTP 405%'
              OR message LIKE '%HTTP_ERROR%HTTP 429%')""")
        now = int(time.time())
        default_groups = [
            ("RUSSIAN","Российские","#35D89A",10),
            ("INTERNATIONAL","Международные","#55C7FF",20),
            ("MESSENGERS","Мессенджеры и соцсети","#7C62FF",30),
            ("INFRASTRUCTURE","Инфраструктура","#FFAD4D",40),
            ("CUSTOM","Пользовательские","#8A96A3",90),
        ]
        for group_key, title, color, sort_order in default_groups:
            conn.execute("""INSERT INTO resource_groups(group_key,title,color,sort_order,created_at,updated_at)
              VALUES(?,?,?,?,?,?)
              ON CONFLICT(group_key) DO NOTHING""",
              (group_key,title,color,sort_order,now,now))
        for row in conn.execute("SELECT DISTINCT group_name FROM resources").fetchall():
            key = row["group_name"]
            conn.execute("""INSERT INTO resource_groups(group_key,title,color,sort_order,created_at,updated_at)
              VALUES(?,?,?,?,?,?)
              ON CONFLICT(group_key) DO NOTHING""",
              (key,key,"#8A96A3",100,now,now))
        conn.execute("""DELETE FROM resource_groups
          WHERE group_key='SELFTEST'
            AND NOT EXISTS(SELECT 1 FROM resources WHERE group_name='SELFTEST')""")
        # 0.4 keeps historical router telemetry but excludes it from live conclusions.
        conn.execute("UPDATE checks SET probe_scope='GLOBAL' WHERE probe_scope='EXTERNAL'")
        conn.execute("UPDATE checks SET probe_scope='LEGACY' WHERE probe_scope='DOMESTIC'")
        conn.execute("UPDATE probes SET scope='GLOBAL' WHERE scope='EXTERNAL'")
        conn.execute("UPDATE probes SET scope='LEGACY' WHERE scope='DOMESTIC'")
        conn.execute("""INSERT INTO probes(probe_key,name,scope,last_seen_at,created_at,updated_at)
          VALUES(?,?,?,?,?,?)
          ON CONFLICT(probe_key) DO UPDATE SET name=excluded.name,scope=excluded.scope,last_seen_at=excluded.last_seen_at,updated_at=excluded.updated_at""",
          (SERVER_PROBE_KEY, SERVER_PROBE_NAME, "GLOBAL", now, now, now))


def seed_defaults() -> None:
    if not SEED_DEFAULTS:
        return
    with db() as conn:
        if conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]:
            return
        now = int(time.time())
        for name, target, group in DEFAULT_RESOURCES:
            match = catalog_match(target)
            conn.execute("""INSERT INTO resources(
              name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at,
              expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,alerts_enabled,
              last_success_at,last_failure_at,catalog_key,allow_http_rejected
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
              match.name if match else name,
              match.target if match else target,
              match.group_key if match else group,
              DEFAULT_INTERVAL,1,now,now,0,200,399,1800,2,1,0,0,
              match.key if match else None, 1 if match else 0,
            ))


def latest_resources() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("""
        SELECT r.*, c.status, c.response_time_ms, c.dns_ms, c.tcp_ms, c.tls_ms, c.http_ms,
               c.http_status, c.resolved_ip, c.message, c.checked_at, c.tls_days_left, c.final_url, c.location,
               (SELECT COUNT(*) FROM incidents i WHERE i.resource_id=r.id AND i.closed_at IS NULL) active_incidents
        FROM resources r
        LEFT JOIN checks c ON c.id=(SELECT id FROM checks WHERE resource_id=r.id AND probe_scope='GLOBAL' ORDER BY checked_at DESC,id DESC LIMIT 1)
        ORDER BY r.group_name,r.name
        """).fetchall()
    return [dict(r) for r in rows]


def get_incidents(active_only: bool=False, limit: int=100) -> list[dict[str, Any]]:
    where = "WHERE i.closed_at IS NULL" if active_only else ""
    with db() as conn:
        rows = conn.execute(f"""SELECT i.*,r.name resource_name,r.target,r.group_name
          FROM incidents i JOIN resources r ON r.id=i.resource_id {where}
          ORDER BY (i.closed_at IS NULL) DESC,i.opened_at DESC LIMIT ?""",(max(1,min(limit,500)),)).fetchall()
    return [dict(r) for r in rows]


def summary() -> dict[str, Any]:
    resources = [r for r in latest_resources() if r["enabled"]]
    checked = [r for r in resources if r.get("checked_at")]
    if not resources:
        return {"availability_index":0,"mode":"NO_DATA","total":0,"checked":0,"available":0,"problematic":0,"last_updated":0,"groups":{},"avg_latency_ms":None,"active_incidents":0,"tls_expiring":0}
    by_group: dict[str,list[dict[str,Any]]] = {}
    for row in resources:
        by_group.setdefault(row["group_name"],[]).append(row)
    if not checked:
        groups={name:{"total":len(rows),"checked":0,"available":0,"problematic":0,"availability":None} for name,rows in by_group.items()}
        return {"availability_index":0,"mode":"INITIALIZING","total":len(resources),"checked":0,"available":0,"problematic":0,"last_updated":0,"groups":groups,"avg_latency_ms":None,"active_incidents":0,"tls_expiring":0}
    available=sum(1 for r in checked if is_reachable(r.get("status")))
    score=round(available/len(checked)*100)
    def ratio(name:str):
        rows=[r for r in by_group.get(name,[]) if r.get("checked_at")]
        return None if not rows else sum(1 for r in rows if is_reachable(r.get("status")))/len(rows)
    ru,intl=ratio("RUSSIAN"),ratio("INTERNATIONAL")
    mode="NO_INTERNET" if score<35 else "RESTRICTED_ACCESS" if ru is not None and intl is not None and intl<.30 and ru>.70 else "PARTIAL_DEGRADATION" if score<70 else "NORMAL"
    groups={}
    for name,rows in by_group.items():
        seen=[r for r in rows if r.get("checked_at")]; ok=sum(1 for r in seen if is_reachable(r.get("status")))
        groups[name]={"total":len(rows),"checked":len(seen),"available":ok,"problematic":len(seen)-ok,"availability":round(ok/len(seen)*100) if seen else None}
    lat=[r["response_time_ms"] for r in checked if r.get("response_time_ms") is not None]
    return {"availability_index":score,"mode":mode,"total":len(resources),"checked":len(checked),"available":available,
      "problematic":len(checked)-available,"last_updated":max(r.get("checked_at") or 0 for r in checked),"groups":groups,
      "avg_latency_ms":round(sum(lat)/len(lat)) if lat else None,"active_incidents":sum(int(r.get("active_incidents") or 0) for r in resources),
      "tls_expiring":sum(1 for r in checked if r.get("tls_days_left") is not None and r["tls_days_left"]<=14)}



def register_probe(probe_key: str, name: str, scope: str = "USER", agent_version: str = "", capabilities: str = "http") -> None:
    now = int(time.time())
    with db() as conn:
        conn.execute("""INSERT INTO probes(probe_key,name,scope,last_seen_at,created_at,updated_at,agent_version,capabilities)
          VALUES(?,?,?,?,?,?,?,?)
          ON CONFLICT(probe_key) DO UPDATE SET name=excluded.name,scope=excluded.scope,last_seen_at=excluded.last_seen_at,
            updated_at=excluded.updated_at,agent_version=excluded.agent_version,capabilities=excluded.capabilities""",
          (probe_key, name, scope, now, now, now, agent_version, capabilities))


def probe_statuses() -> list[dict[str, Any]]:
    now = int(time.time())
    with db() as conn:
        rows = conn.execute("SELECT * FROM probes ORDER BY scope, name").fetchall()
    return [{
        **dict(r),
        "online": bool(r["last_seen_at"] and now - r["last_seen_at"] <= CLIENT_PROBE_STALE_SECONDS),
        "age_seconds": max(0, now - int(r["last_seen_at"] or 0)) if r["last_seen_at"] else None,
    } for r in rows]


def _latest_probe_check(conn: sqlite3.Connection, resource_id: int, scope: str):
    return conn.execute("""SELECT * FROM checks WHERE resource_id=? AND probe_scope=?
      ORDER BY checked_at DESC,id DESC LIMIT 1""", (resource_id, scope)).fetchone()


def resource_matrix() -> list[dict[str, Any]]:
    now = int(time.time())
    with db() as conn:
        resources = conn.execute("SELECT * FROM resources ORDER BY group_name,name").fetchall()
        probes = {r["probe_key"]: dict(r) for r in conn.execute("SELECT * FROM probes").fetchall()}
        result = []
        for r in resources:
            ext = _latest_probe_check(conn, r["id"], "GLOBAL")
            user = _latest_probe_check(conn, r["id"], "USER")
            ext_d = dict(ext) if ext else None
            user_d = dict(user) if user else None
            user_fresh = False
            if user_d:
                p = probes.get(user_d.get("probe_key"))
                user_fresh = bool(p and p.get("last_seen_at") and now - int(p["last_seen_at"]) <= CLIENT_PROBE_STALE_SECONDS)
            current_user = user_d if user_fresh else None
            diagnostic = conn.execute("""SELECT classification,confidence,result_summary_json,completed_at
              FROM diagnostic_jobs WHERE resource_id=? AND status='finished'
              ORDER BY completed_at DESC,id DESC LIMIT 1""", (r["id"],)).fetchone()
            evidence_rows = conn.execute("""SELECT provider,status,classification,confidence,summary_json,fetched_at,expires_at
              FROM external_evidence WHERE (resource_id=? OR resource_id IS NULL) AND expires_at>?
              ORDER BY fetched_at DESC,id DESC""", (r["id"], now)).fetchall()
            evidence_by_provider = {}
            for evidence in evidence_rows:
                if evidence["provider"] not in evidence_by_provider:
                    item = dict(evidence)
                    item["summary"] = json.loads(item.pop("summary_json") or "{}")
                    evidence_by_provider[evidence["provider"]] = item
            diagnostic_summary = json.loads(diagnostic["result_summary_json"] or "{}") if diagnostic else {}
            external_classification = diagnostic["classification"] if diagnostic else None
            assessment = assess_incident(
                ext_d.get("status") if ext_d else None,
                current_user.get("status") if current_user else None,
                global_slow=bool(ext_d and ext_d.get("response_time_ms") is not None and ext_d["response_time_ms"] >= r["slow_threshold_ms"]),
                user_slow=bool(current_user and current_user.get("response_time_ms") is not None and current_user["response_time_ms"] >= r["slow_threshold_ms"]),
                external_failures=int(diagnostic_summary.get("failed") or 0),
                external_classification=external_classification,
                ooni_signal=evidence_by_provider.get("ooni", {}).get("classification") == "POSSIBLE_FILTERING",
                ioda_signal=evidence_by_provider.get("ioda", {}).get("classification") == "REGIONAL_OUTAGE",
            )
            legacy = {
                "status": ext_d.get("status") if ext_d else None,
                "response_time_ms": ext_d.get("response_time_ms") if ext_d else None,
                "dns_ms": ext_d.get("dns_ms") if ext_d else None,
                "tcp_ms": ext_d.get("tcp_ms") if ext_d else None,
                "tls_ms": ext_d.get("tls_ms") if ext_d else None,
                "http_ms": ext_d.get("http_ms") if ext_d else None,
                "http_status": ext_d.get("http_status") if ext_d else None,
                "resolved_ip": ext_d.get("resolved_ip") if ext_d else None,
                "message": ext_d.get("message") if ext_d else None,
                "checked_at": ext_d.get("checked_at") if ext_d else None,
                "tls_days_left": ext_d.get("tls_days_left") if ext_d else None,
            }
            result.append({
                **dict(r),
                **legacy,
                "global": ext_d,
                "your_network": current_user,
                "your_network_available": bool(current_user),
                "your_network_stale": bool(user_d and not user_fresh),
                "diagnosis": assessment.classification.value,
                "diagnosis_text": assessment.explanation,
                "confidence": assessment.confidence,
                "external_diagnostic": ({
                    "classification": diagnostic["classification"],
                    "confidence": diagnostic["confidence"],
                    "summary": diagnostic_summary,
                    "completed_at": diagnostic["completed_at"],
                } if diagnostic else None),
                "evidence": list(evidence_by_provider.values()),
            })
    return result


def dual_summary() -> dict[str, Any]:
    rows = [r for r in resource_matrix() if r["enabled"]]
    probes = probe_statuses()
    user_online = any(p["scope"] == "USER" and p["online"] for p in probes)
    counts = {
        "ok": 0, "degraded": 0, "down": 0, "local": 0, "unknown": 0,
    }
    user_lat = []
    last_updated = 0
    groups: dict[str, dict[str, int]] = {}
    for r in rows:
        d = r["diagnosis"]
        if d == "OK": counts["ok"] += 1
        elif d == "DEGRADED": counts["degraded"] += 1
        elif d in {"SERVICE_DOWN","REGIONAL_OUTAGE","DNS_FAILURE"}: counts["down"] += 1
        elif d in {"LOCAL_NETWORK","ISP_OUTAGE","ROUTING_FAILURE","POSSIBLE_FILTERING"}: counts["local"] += 1
        else: counts["unknown"] += 1
        g = groups.setdefault(r["group_name"], {"total":0,"ok":0,"degraded":0,"down":0,"local":0,"unknown":0})
        g["total"] += 1
        if d == "OK": g["ok"] += 1
        elif d == "DEGRADED": g["degraded"] += 1
        elif d in {"SERVICE_DOWN","REGIONAL_OUTAGE","DNS_FAILURE"}: g["down"] += 1
        elif d in {"LOCAL_NETWORK","ISP_OUTAGE","ROUTING_FAILURE","POSSIBLE_FILTERING"}: g["local"] += 1
        else: g["unknown"] += 1
        if r["your_network"]:
            last_updated = max(last_updated, int(r["your_network"]["checked_at"] or 0))
            if r["your_network"].get("response_time_ms") is not None:
                user_lat.append(int(r["your_network"]["response_time_ms"]))
        elif r["global"]:
            last_updated = max(last_updated, int(r["global"]["checked_at"] or 0))
    confirmed = max(1, len(rows) - counts["unknown"])
    score = round((counts["ok"] + counts["degraded"]) / confirmed * 100) if rows else None
    mode = "OUTAGE" if counts["down"] else "YOUR_NETWORK_ISSUE" if counts["local"] else "DEGRADED" if counts["degraded"] else "NORMAL" if rows else "NO_DATA"
    return {
        "mode": mode, "availability_index": score, "total": len(rows),
        "last_updated": last_updated, "groups": groups, "probes": probes,
        "your_network_available": user_online,
        "your_network_state": "connected" if user_online else "unavailable",
        "avg_user_latency_ms": round(sum(user_lat)/len(user_lat)) if user_lat else None,
        **counts,
    }



def resource_groups() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("""SELECT g.*,
          (SELECT COUNT(*) FROM resources r WHERE r.group_name=g.group_key) resource_count
          FROM resource_groups g ORDER BY g.sort_order,g.title""").fetchall()
    return [dict(r) for r in rows]
