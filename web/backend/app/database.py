from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from .config import AGENT_STALE_SECONDS, DB_PATH, DEFAULT_INTERVAL, DEFAULT_RESOURCES, SEED_DEFAULTS, SERVER_PROBE_KEY, SERVER_PROBE_NAME


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
        """)
        for table, name, ddl in [
            ("resources","expected_status_min","INTEGER NOT NULL DEFAULT 200"),
            ("resources","expected_status_max","INTEGER NOT NULL DEFAULT 399"),
            ("resources","slow_threshold_ms","INTEGER NOT NULL DEFAULT 1500"),
            ("resources","failure_threshold","INTEGER NOT NULL DEFAULT 2"),
            ("resources","alerts_enabled","INTEGER NOT NULL DEFAULT 1"),
            ("resources","last_success_at","INTEGER NOT NULL DEFAULT 0"),
            ("resources","last_failure_at","INTEGER NOT NULL DEFAULT 0"),
            ("checks","tls_days_left","INTEGER"),
            ("checks","final_url","TEXT"),
            ("checks","location","TEXT"),
            ("checks","probe_key","TEXT NOT NULL DEFAULT 'VPS_EU'"),
            ("checks","probe_scope","TEXT NOT NULL DEFAULT 'EXTERNAL'"),
        ]:
            _ensure_column(conn, table, name, ddl)
        now = int(time.time())
        conn.execute("""INSERT INTO probes(probe_key,name,scope,last_seen_at,created_at,updated_at)
          VALUES(?,?,?,?,?,?)
          ON CONFLICT(probe_key) DO UPDATE SET name=excluded.name,scope=excluded.scope,last_seen_at=excluded.last_seen_at,updated_at=excluded.updated_at""",
          (SERVER_PROBE_KEY, SERVER_PROBE_NAME, "EXTERNAL", now, now, now))


def seed_defaults() -> None:
    if not SEED_DEFAULTS:
        return
    with db() as conn:
        if conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]:
            return
        now = int(time.time())
        for name, target, group in DEFAULT_RESOURCES:
            conn.execute("""INSERT INTO resources(
              name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at,
              expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,alerts_enabled,
              last_success_at,last_failure_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name,target,group,DEFAULT_INTERVAL,1,now,now,0,200,399,1800,2,1,0,0))


def latest_resources() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("""
        SELECT r.*, c.status, c.response_time_ms, c.dns_ms, c.tcp_ms, c.tls_ms, c.http_ms,
               c.http_status, c.resolved_ip, c.message, c.checked_at, c.tls_days_left, c.final_url, c.location,
               (SELECT COUNT(*) FROM incidents i WHERE i.resource_id=r.id AND i.closed_at IS NULL) active_incidents
        FROM resources r
        LEFT JOIN checks c ON c.id=(SELECT id FROM checks WHERE resource_id=r.id AND probe_scope='EXTERNAL' ORDER BY checked_at DESC,id DESC LIMIT 1)
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
    available=sum(1 for r in checked if r.get("status")=="OK")
    score=round(available/len(checked)*100)
    def ratio(name:str):
        rows=[r for r in by_group.get(name,[]) if r.get("checked_at")]
        return None if not rows else sum(1 for r in rows if r.get("status")=="OK")/len(rows)
    ru,intl=ratio("RUSSIAN"),ratio("INTERNATIONAL")
    mode="NO_INTERNET" if score<35 else "RESTRICTED_ACCESS" if ru is not None and intl is not None and intl<.30 and ru>.70 else "PARTIAL_DEGRADATION" if score<70 else "NORMAL"
    groups={}
    for name,rows in by_group.items():
        seen=[r for r in rows if r.get("checked_at")]; ok=sum(1 for r in seen if r.get("status")=="OK")
        groups[name]={"total":len(rows),"checked":len(seen),"available":ok,"problematic":len(seen)-ok,"availability":round(ok/len(seen)*100) if seen else None}
    lat=[r["response_time_ms"] for r in checked if r.get("response_time_ms") is not None]
    return {"availability_index":score,"mode":mode,"total":len(resources),"checked":len(checked),"available":available,
      "problematic":len(checked)-available,"last_updated":max(r.get("checked_at") or 0 for r in checked),"groups":groups,
      "avg_latency_ms":round(sum(lat)/len(lat)) if lat else None,"active_incidents":sum(int(r.get("active_incidents") or 0) for r in resources),
      "tls_expiring":sum(1 for r in checked if r.get("tls_days_left") is not None and r["tls_days_left"]<=14)}



def register_probe(probe_key: str, name: str, scope: str = "DOMESTIC") -> None:
    now = int(time.time())
    with db() as conn:
        conn.execute("""INSERT INTO probes(probe_key,name,scope,last_seen_at,created_at,updated_at)
          VALUES(?,?,?,?,?,?)
          ON CONFLICT(probe_key) DO UPDATE SET name=excluded.name,scope=excluded.scope,last_seen_at=excluded.last_seen_at,updated_at=excluded.updated_at""",
          (probe_key, name, scope, now, now, now))


def probe_statuses() -> list[dict[str, Any]]:
    now = int(time.time())
    with db() as conn:
        rows = conn.execute("SELECT * FROM probes ORDER BY scope, name").fetchall()
    return [{
        **dict(r),
        "online": bool(r["last_seen_at"] and now - r["last_seen_at"] <= AGENT_STALE_SECONDS),
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
            ext = _latest_probe_check(conn, r["id"], "EXTERNAL")
            dom = _latest_probe_check(conn, r["id"], "DOMESTIC")
            ext_d = dict(ext) if ext else None
            dom_d = dict(dom) if dom else None
            dom_fresh = False
            if dom_d:
                p = probes.get(dom_d.get("probe_key"))
                dom_fresh = bool(p and p.get("last_seen_at") and now - int(p["last_seen_at"]) <= AGENT_STALE_SECONDS)
            if not dom_d or not dom_fresh:
                diagnosis = "DOMESTIC_UNKNOWN"
                diagnosis_text = "Нет актуальных данных из российского контура"
                confidence = "none"
            elif ext_d and ext_d.get("status") == "OK" and dom_d.get("status") == "OK":
                diagnosis = "AVAILABLE"
                diagnosis_text = "Доступен снаружи и из российского контура"
                confidence = "high"
            elif ext_d and ext_d.get("status") == "OK" and dom_d.get("status") != "OK":
                diagnosis = "LIKELY_RESTRICTION"
                diagnosis_text = "Снаружи доступен, из российского контура недоступен"
                confidence = "medium"
            elif ext_d and ext_d.get("status") != "OK" and dom_d.get("status") != "OK":
                diagnosis = "LIKELY_OUTAGE"
                diagnosis_text = "Недоступен из обеих точек наблюдения"
                confidence = "medium"
            elif ext_d and ext_d.get("status") != "OK" and dom_d.get("status") == "OK":
                diagnosis = "EXTERNAL_PATH_ISSUE"
                diagnosis_text = "В российском контуре доступен, внешний probe видит проблему"
                confidence = "medium"
            else:
                diagnosis = "INSUFFICIENT_DATA"
                diagnosis_text = "Недостаточно данных для классификации"
                confidence = "none"
            result.append({
                **dict(r),
                "external": ext_d,
                "domestic": dom_d if dom_fresh else None,
                "domestic_stale": bool(dom_d and not dom_fresh),
                "diagnosis": diagnosis,
                "diagnosis_text": diagnosis_text,
                "confidence": confidence,
            })
    return result


def dual_summary() -> dict[str, Any]:
    rows = [r for r in resource_matrix() if r["enabled"]]
    probes = probe_statuses()
    domestic_online = any(p["scope"] == "DOMESTIC" and p["online"] for p in probes)
    counts = {
        "available": 0, "likely_restriction": 0, "likely_outage": 0,
        "external_path_issue": 0, "unknown": 0,
    }
    domestic_lat = []
    last_updated = 0
    groups: dict[str, dict[str, int]] = {}
    for r in rows:
        d = r["diagnosis"]
        if d == "AVAILABLE": counts["available"] += 1
        elif d == "LIKELY_RESTRICTION": counts["likely_restriction"] += 1
        elif d == "LIKELY_OUTAGE": counts["likely_outage"] += 1
        elif d == "EXTERNAL_PATH_ISSUE": counts["external_path_issue"] += 1
        else: counts["unknown"] += 1
        g = groups.setdefault(r["group_name"], {"total":0,"available":0,"restriction":0,"outage":0,"unknown":0})
        g["total"] += 1
        if d == "AVAILABLE": g["available"] += 1
        elif d == "LIKELY_RESTRICTION": g["restriction"] += 1
        elif d == "LIKELY_OUTAGE": g["outage"] += 1
        else: g["unknown"] += 1
        if r["domestic"]:
            last_updated = max(last_updated, int(r["domestic"]["checked_at"] or 0))
            if r["domestic"].get("response_time_ms") is not None:
                domestic_lat.append(int(r["domestic"]["response_time_ms"]))
        elif r["external"]:
            last_updated = max(last_updated, int(r["external"]["checked_at"] or 0))
    if not domestic_online:
        mode = "NO_DOMESTIC_PROBE"
        score = None
    else:
        confirmed = max(1, len(rows) - counts["unknown"])
        score = round(counts["available"] / confirmed * 100)
        if counts["likely_restriction"]:
            mode = "RESTRICTIONS_DETECTED"
        elif counts["likely_outage"]:
            mode = "OUTAGES_DETECTED"
        elif counts["external_path_issue"]:
            mode = "PROBE_PATH_ISSUES"
        else:
            mode = "NORMAL"
    return {
        "mode": mode, "availability_index": score, "total": len(rows),
        "last_updated": last_updated, "groups": groups, "probes": probes,
        "domestic_probe_online": domestic_online,
        "avg_domestic_latency_ms": round(sum(domestic_lat)/len(domestic_lat)) if domestic_lat else None,
        **counts,
    }
