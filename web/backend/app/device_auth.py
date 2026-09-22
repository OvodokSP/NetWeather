from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from .database import db


_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _digest(secret: str, purpose: str, value: str) -> str:
    return hmac.new(secret.encode("utf-8"), f"{purpose}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _normalize_code(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def _new_code() -> str:
    raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


@dataclass(frozen=True)
class DeviceIdentity:
    device_id: str
    name: str


def start_authorization(
    *, device_id: str, device_name: str, app_version: str, server_secret: str,
    ttl_seconds: int, poll_interval_seconds: int,
) -> dict:
    now = int(time.time())
    expires_at = now + max(60, ttl_seconds)
    session_id = secrets.token_urlsafe(24)
    poll_secret = secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute(
            """INSERT INTO devices(device_id,name,app_version,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET name=excluded.name,
                 app_version=excluded.app_version,updated_at=excluded.updated_at""",
            (device_id, device_name.strip(), app_version.strip(), "PENDING", now, now),
        )
        conn.execute(
            "UPDATE device_authorizations SET status='SUPERSEDED' WHERE device_id=? AND status='PENDING'",
            (device_id,),
        )
        for _ in range(12):
            user_code = _new_code()
            code_hash = _digest(server_secret, "device-code", _normalize_code(user_code))
            if not conn.execute(
                "SELECT 1 FROM device_authorizations WHERE user_code_hash=? AND status='PENDING'",
                (code_hash,),
            ).fetchone():
                break
        else:
            raise RuntimeError("Unable to allocate a unique device code")
        conn.execute(
            """INSERT INTO device_authorizations(
                 session_id,device_id,user_code_hash,poll_secret_hash,status,created_at,expires_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (session_id, device_id, code_hash, _digest(server_secret, "device-poll", poll_secret),
             "PENDING", now, expires_at),
        )
    return {
        "session_id": session_id,
        "poll_secret": poll_secret,
        "user_code": user_code,
        "expires_at": expires_at,
        "expires_in": expires_at - now,
        "interval": max(3, poll_interval_seconds),
    }


def approve_authorization(user_code: str, server_secret: str) -> dict | None:
    now = int(time.time())
    code_hash = _digest(server_secret, "device-code", _normalize_code(user_code))
    with db() as conn:
        row = conn.execute(
            """SELECT a.session_id,a.device_id,d.name,a.expires_at
               FROM device_authorizations a JOIN devices d ON d.device_id=a.device_id
               WHERE a.user_code_hash=? AND a.status='PENDING'""",
            (code_hash,),
        ).fetchone()
        if not row or int(row["expires_at"]) <= now:
            if row:
                conn.execute("UPDATE device_authorizations SET status='EXPIRED' WHERE session_id=?", (row["session_id"],))
            return None
        conn.execute(
            "UPDATE device_authorizations SET status='APPROVED',approved_at=? WHERE session_id=?",
            (now, row["session_id"]),
        )
        conn.execute(
            "UPDATE devices SET status='APPROVED',approved_at=?,revoked_at=NULL,updated_at=? WHERE device_id=?",
            (now, now, row["device_id"]),
        )
    return {"device_id": row["device_id"], "device_name": row["name"], "approved_at": now}


def poll_authorization(session_id: str, poll_secret: str, server_secret: str, token_max_age: int) -> dict:
    now = int(time.time())
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM device_authorizations WHERE session_id=?", (session_id,)
        ).fetchone()
        if not row or not hmac.compare_digest(
            row["poll_secret_hash"], _digest(server_secret, "device-poll", poll_secret)
        ):
            return {"status": "invalid"}
        if int(row["expires_at"]) <= now and row["status"] == "PENDING":
            conn.execute("UPDATE device_authorizations SET status='EXPIRED' WHERE session_id=?", (session_id,))
            return {"status": "expired"}
        if row["status"] == "PENDING":
            return {"status": "pending", "expires_in": max(0, int(row["expires_at"]) - now)}
        if row["status"] == "APPROVED" and row["delivered_at"] is None:
            token = "nwdev_" + secrets.token_urlsafe(32)
            conn.execute(
                "UPDATE devices SET token_hash=?,token_expires_at=?,status='ACTIVE',last_seen_at=?,updated_at=? WHERE device_id=?",
                (_digest(server_secret, "device-token", token), now + max(3600, token_max_age), now, now, row["device_id"]),
            )
            conn.execute(
                "UPDATE device_authorizations SET status='DELIVERED',delivered_at=? WHERE session_id=?",
                (now, session_id),
            )
            return {
                "status": "authorized", "access_token": token, "token_type": "Bearer",
                "expires_in": max(3600, token_max_age), "device_id": row["device_id"],
            }
        if row["status"] == "DELIVERED":
            return {"status": "delivered"}
        return {"status": str(row["status"]).lower()}


def authenticate_device(authorization: str | None, server_secret: str) -> DeviceIdentity | None:
    if not authorization or not authorization.startswith("Bearer nwdev_"):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    token_hash = _digest(server_secret, "device-token", token)
    now = int(time.time())
    with db() as conn:
        row = conn.execute(
            """SELECT device_id,name FROM devices
               WHERE token_hash=? AND status='ACTIVE' AND revoked_at IS NULL
                 AND (token_expires_at IS NULL OR token_expires_at>?)""",
            (token_hash, now),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE devices SET last_seen_at=?,updated_at=? WHERE device_id=?",
            (now, now, row["device_id"]),
        )
    return DeviceIdentity(row["device_id"], row["name"])


def list_devices() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """SELECT device_id,name,app_version,status,created_at,approved_at,last_seen_at,revoked_at,token_expires_at
               FROM devices ORDER BY created_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def revoke_device(device_id: str) -> bool:
    now = int(time.time())
    with db() as conn:
        cur = conn.execute(
            """UPDATE devices SET status='REVOKED',token_hash=NULL,revoked_at=?,updated_at=?
               WHERE device_id=?""",
            (now, now, device_id),
        )
        conn.execute(
            "UPDATE device_authorizations SET status='REVOKED' WHERE device_id=? AND status IN ('PENDING','APPROVED')",
            (device_id,),
        )
    return cur.rowcount > 0
