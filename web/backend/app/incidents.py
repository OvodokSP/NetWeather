from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .config import ALERT_WEBHOOK_URL, SERVER_PROBE_KEY
from .database import db
from .availability import is_reachable


def _open(conn, resource_id: int, kind: str, severity: str, message: str, now: int):
    if conn.execute(
        "SELECT id FROM incidents WHERE resource_id=? AND kind=? AND closed_at IS NULL LIMIT 1",
        (resource_id, kind),
    ).fetchone():
        return None
    return int(conn.execute(
        "INSERT INTO incidents(resource_id,kind,severity,opened_at,message) VALUES(?,?,?,?,?)",
        (resource_id, kind, severity, now, message),
    ).lastrowid)


def _close(conn, resource_id: int, kind: str, now: int):
    rows = conn.execute(
        "SELECT id FROM incidents WHERE resource_id=? AND kind=? AND closed_at IS NULL",
        (resource_id, kind),
    ).fetchall()
    if rows:
        conn.execute(
            "UPDATE incidents SET closed_at=? WHERE resource_id=? AND kind=? AND closed_at IS NULL",
            (now, resource_id, kind),
        )
    return [int(r["id"]) for r in rows]


def _post(payload):
    if not ALERT_WEBHOOK_URL:
        return
    try:
        httpx.post(ALERT_WEBHOOK_URL, json=payload, timeout=4)
    except Exception:
        pass


def _notify(payload):
    if not ALERT_WEBHOOK_URL:
        return
    try:
        asyncio.get_running_loop().run_in_executor(None, _post, payload)
    except RuntimeError:
        pass


def _notice(event: str, iid: int, resource: str, kind: str, severity: str, message: str, now: int):
    return {
        "event": event,
        "incident_id": iid,
        "resource": resource,
        "kind": kind,
        "severity": severity,
        "message": message,
        "time": now,
    }


def _evaluate_restriction(conn, resource, now: int, notices: list[dict[str, Any]]) -> None:
    threshold = max(1, int(resource["failure_threshold"] or 2))
    ext = conn.execute(
        """SELECT * FROM checks WHERE resource_id=? AND probe_scope='EXTERNAL'
           ORDER BY checked_at DESC,id DESC LIMIT 1""",
        (resource["id"],),
    ).fetchone()
    dom = conn.execute(
        """SELECT * FROM checks WHERE resource_id=? AND probe_scope='DOMESTIC'
           ORDER BY checked_at DESC,id DESC LIMIT 1""",
        (resource["id"],),
    ).fetchone()
    if not ext or not dom:
        return

    recent_dom = conn.execute(
        """SELECT status FROM checks WHERE resource_id=? AND probe_scope='DOMESTIC' AND probe_key=?
           ORDER BY checked_at DESC,id DESC LIMIT ?""",
        (resource["id"], dom["probe_key"], threshold),
    ).fetchall()
    domestic_confirmed_fail = len(recent_dom) >= threshold and all(not is_reachable(r["status"]) for r in recent_dom)
    restriction = is_reachable(ext["status"]) and domestic_confirmed_fail

    if restriction:
        msg = (
            f"{resource['name']}: внешний probe отвечает OK, "
            f"российский probe {dom['probe_key']} получает {dom['status']} — {dom['message']}"
        )
        iid = _open(conn, resource["id"], "RESTRICTION", "critical", msg, now)
        if iid:
            notices.append(_notice("incident_opened", iid, resource["name"], "RESTRICTION", "critical", msg, now))
    else:
        for iid in _close(conn, resource["id"], "RESTRICTION", now):
            notices.append(_notice(
                "incident_closed", iid, resource["name"], "RESTRICTION", "info",
                "Различие между внешним и российским контуром исчезло", now,
            ))


def write_check(
    resource_id: int,
    payload: dict[str, Any],
    probe_key: str = SERVER_PROBE_KEY,
    probe_scope: str = "EXTERNAL",
) -> None:
    now = int(time.time())
    notices: list[dict[str, Any]] = []
    probe_scope = probe_scope.upper()
    with db() as conn:
        resource = conn.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
        if not resource:
            return
        conn.execute(
            "UPDATE probes SET last_seen_at=?,updated_at=? WHERE probe_key=?",
            (now, now, probe_key),
        )
        conn.execute(
            """INSERT INTO checks(
                 resource_id,checked_at,status,response_time_ms,dns_ms,tcp_ms,tls_ms,http_ms,
                 http_status,resolved_ip,message,tls_days_left,final_url,location,probe_key,probe_scope
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                resource_id, now, payload["status"], payload["response_time_ms"], payload.get("dns_ms"),
                payload.get("tcp_ms"), payload.get("tls_ms"), payload.get("http_ms"), payload.get("http_status"),
                payload.get("resolved_ip"), payload.get("message", ""), payload.get("tls_days_left"),
                payload.get("final_url"), payload.get("location"), probe_key, probe_scope,
            ),
        )

        if probe_scope == "EXTERNAL":
            if is_reachable(payload["status"]):
                conn.execute(
                    "UPDATE resources SET last_checked_at=?,last_success_at=?,updated_at=? WHERE id=?",
                    (now, now, now, resource_id),
                )
            else:
                conn.execute(
                    "UPDATE resources SET last_checked_at=?,last_failure_at=?,updated_at=? WHERE id=?",
                    (now, now, now, resource_id),
                )

        conn.execute("DELETE FROM checks WHERE checked_at<?", (now - 2592000,))
        if not resource["alerts_enabled"]:
            return

        threshold = max(1, int(resource["failure_threshold"] or 2))

        if probe_scope == "EXTERNAL":
            recent = conn.execute(
                """SELECT status FROM checks WHERE resource_id=? AND probe_scope='EXTERNAL'
                   ORDER BY checked_at DESC,id DESC LIMIT ?""",
                (resource_id, threshold),
            ).fetchall()
            failing = len(recent) >= threshold and all(not is_reachable(x["status"]) for x in recent)
            if failing:
                msg = f"{resource['name']}: {payload['status']} — {payload.get('message','')}"
                iid = _open(conn, resource_id, "DOWN", "critical", msg, now)
                if iid:
                    notices.append(_notice("incident_opened", iid, resource["name"], "DOWN", "critical", msg, now))
            elif is_reachable(payload["status"]):
                for iid in _close(conn, resource_id, "DOWN", now):
                    notices.append(_notice(
                        "incident_closed", iid, resource["name"], "DOWN", "info",
                        "Внешняя доступность восстановлена", now,
                    ))

            slow = is_reachable(payload["status"]) and payload["response_time_ms"] >= int(resource["slow_threshold_ms"] or 1500)
            if slow:
                msg = (
                    f"{resource['name']}: внешний отклик {payload['response_time_ms']} мс "
                    f"выше порога {resource['slow_threshold_ms']} мс"
                )
                iid = _open(conn, resource_id, "SLOW", "warning", msg, now)
                if iid:
                    notices.append(_notice("incident_opened", iid, resource["name"], "SLOW", "warning", msg, now))
            elif is_reachable(payload["status"]):
                for iid in _close(conn, resource_id, "SLOW", now):
                    notices.append(_notice(
                        "incident_closed", iid, resource["name"], "SLOW", "info",
                        "Внешняя задержка вернулась в норму", now,
                    ))

            days = payload.get("tls_days_left")
            if days is not None and days <= 14:
                msg = f"{resource['name']}: TLS-сертификат истекает через {days} дн."
                iid = _open(conn, resource_id, "TLS_EXPIRY", "warning", msg, now)
                if iid:
                    notices.append(_notice(
                        "incident_opened", iid, resource["name"], "TLS_EXPIRY", "warning", msg, now,
                    ))
            elif days is not None and days > 14:
                for iid in _close(conn, resource_id, "TLS_EXPIRY", now):
                    notices.append(_notice(
                        "incident_closed", iid, resource["name"], "TLS_EXPIRY", "info",
                        "Срок TLS снова вне порога тревоги", now,
                    ))

        _evaluate_restriction(conn, resource, now, notices)

    for notice in notices:
        _notify(notice)
