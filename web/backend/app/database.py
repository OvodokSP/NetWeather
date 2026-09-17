from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from typing import Any

from .config import DB_PATH, DEFAULT_INTERVAL, DEFAULT_RESOURCES, SEED_DEFAULTS


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
        ]:
            _ensure_column(conn, table, name, ddl)


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
        LEFT JOIN checks c ON c.id=(SELECT id FROM checks WHERE resource_id=r.id ORDER BY checked_at DESC,id DESC LIMIT 1)
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
      "avg_latency_ms":round(sum(lat)/len(lat)) if lat else None,"active_incidents":sum(1 for r in resources if r.get("active_incidents")),
      "tls_expiring":sum(1 for r in checked if r.get("tls_days_left") is not None and r["tls_days_left"]<=14)}
