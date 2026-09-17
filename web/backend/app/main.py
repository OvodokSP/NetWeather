from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import socket
import sqlite3
import ssl
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("NETWEATHER_DB", "/data/netweather.db"))
API_TOKEN = os.getenv("NETWEATHER_API_TOKEN", "")
ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"
DEFAULT_INTERVAL = int(os.getenv("DEFAULT_INTERVAL_SECONDS", "60"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))

class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=2048)
    group_name: str = Field(default="CUSTOM", max_length=40)
    interval_seconds: int = Field(default=DEFAULT_INTERVAL, ge=30, le=86400)
    enabled: bool = True

class ResourcePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target: str | None = Field(default=None, min_length=1, max_length=2048)
    group_name: str | None = Field(default=None, max_length=40)
    interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    enabled: bool | None = None


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target TEXT NOT NULL,
                group_name TEXT NOT NULL DEFAULT 'CUSTOM',
                interval_seconds INTEGER NOT NULL DEFAULT 60,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_checked_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                checked_at INTEGER NOT NULL,
                status TEXT NOT NULL,
                response_time_ms INTEGER NOT NULL,
                dns_ms INTEGER,
                tcp_ms INTEGER,
                tls_ms INTEGER,
                http_ms INTEGER,
                http_status INTEGER,
                resolved_ip TEXT,
                message TEXT,
                FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_checks_resource_time ON checks(resource_id, checked_at DESC);
            """
        )


def require_token(authorization: str | None = Header(default=None)) -> None:
    if not API_TOKEN:
        raise HTTPException(503, "NETWEATHER_API_TOKEN is not configured")
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(401, "Invalid API token")


def normalize_target(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Target must be a valid HTTP/HTTPS URL or hostname")
    return value


async def resolve_host(host: str) -> tuple[str, float]:
    started = time.perf_counter()
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    if not infos:
        raise OSError("DNS returned no addresses")
    ip = infos[0][4][0]
    address = ipaddress.ip_address(ip)
    if not ALLOW_PRIVATE_TARGETS and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise PermissionError("Private, loopback and link-local targets are blocked")
    return ip, (time.perf_counter() - started) * 1000


async def tcp_probe(host: str, port: int) -> float:
    started = time.perf_counter()
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=4)
    writer.close()
    await writer.wait_closed()
    return (time.perf_counter() - started) * 1000


async def tls_probe(host: str, port: int) -> float:
    started = time.perf_counter()
    context = ssl.create_default_context()
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port, ssl=context, server_hostname=host), timeout=4)
    writer.close()
    await writer.wait_closed()
    return (time.perf_counter() - started) * 1000


async def perform_check(resource: sqlite3.Row) -> dict[str, Any]:
    target = normalize_target(resource["target"])
    parsed = urlparse(target)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    started = time.perf_counter()
    result: dict[str, Any] = {
        "status": "UNKNOWN_ERROR",
        "response_time_ms": 0,
        "dns_ms": None,
        "tcp_ms": None,
        "tls_ms": None,
        "http_ms": None,
        "http_status": None,
        "resolved_ip": None,
        "message": "",
    }
    try:
        ip, dns_ms = await resolve_host(host)
        result["resolved_ip"] = ip
        result["dns_ms"] = round(dns_ms)
    except PermissionError as exc:
        result["status"] = "BLOCKED_TARGET"
        result["message"] = str(exc)
        result["response_time_ms"] = round((time.perf_counter() - started) * 1000)
        return result
    except Exception as exc:
        result["status"] = "DNS_ERROR"
        result["message"] = str(exc)
        result["response_time_ms"] = round((time.perf_counter() - started) * 1000)
        return result

    try:
        result["tcp_ms"] = round(await tcp_probe(host, port))
    except Exception as exc:
        result["status"] = "TCP_ERROR"
        result["message"] = str(exc)
        result["response_time_ms"] = round((time.perf_counter() - started) * 1000)
        return result

    if parsed.scheme == "https":
        try:
            result["tls_ms"] = round(await tls_probe(host, port))
        except Exception as exc:
            result["status"] = "TLS_ERROR"
            result["message"] = str(exc)
            result["response_time_ms"] = round((time.perf_counter() - started) * 1000)
            return result

    try:
        http_started = time.perf_counter()
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers={"User-Agent": "NetWeather/1.0"}) as client:
            response = await client.get(target)
        result["http_ms"] = round((time.perf_counter() - http_started) * 1000)
        result["http_status"] = response.status_code
        if 200 <= response.status_code < 400:
            result["status"] = "OK"
            result["message"] = f"HTTP {response.status_code}"
        else:
            result["status"] = "HTTP_ERROR"
            result["message"] = f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        result["status"] = "TIMEOUT"
        result["message"] = "HTTP timeout"
    except Exception as exc:
        result["status"] = "HTTP_ERROR"
        result["message"] = str(exc)

    result["response_time_ms"] = round((time.perf_counter() - started) * 1000)
    return result


def write_check(resource_id: int, payload: dict[str, Any]) -> None:
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """INSERT INTO checks(resource_id, checked_at, status, response_time_ms, dns_ms, tcp_ms, tls_ms, http_ms, http_status, resolved_ip, message)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (resource_id, now, payload["status"], payload["response_time_ms"], payload["dns_ms"], payload["tcp_ms"], payload["tls_ms"], payload["http_ms"], payload["http_status"], payload["resolved_ip"], payload["message"]),
        )
        conn.execute("UPDATE resources SET last_checked_at=?, updated_at=? WHERE id=?", (now, now, resource_id))
        conn.execute("DELETE FROM checks WHERE checked_at < ?", (now - 60 * 60 * 24 * 30,))


async def check_resource(resource_id: int) -> dict[str, Any]:
    with db() as conn:
        resource = conn.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
    if not resource:
        raise HTTPException(404, "Resource not found")
    payload = await perform_check(resource)
    write_check(resource_id, payload)
    return payload


async def scheduler() -> None:
    while True:
        now = int(time.time())
        with db() as conn:
            due = conn.execute(
                "SELECT * FROM resources WHERE enabled=1 AND (? - last_checked_at) >= interval_seconds ORDER BY last_checked_at ASC LIMIT 25",
                (now,),
            ).fetchall()
        if due:
            await asyncio.gather(*(run_scheduled(row) for row in due))
        await asyncio.sleep(5)


async def run_scheduled(row: sqlite3.Row) -> None:
    try:
        payload = await perform_check(row)
        write_check(row["id"], payload)
    except Exception as exc:
        write_check(row["id"], {"status":"UNKNOWN_ERROR","response_time_ms":0,"dns_ms":None,"tcp_ms":None,"tls_ms":None,"http_ms":None,"http_status":None,"resolved_ip":None,"message":str(exc)})


def latest_resources() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT r.*, c.status, c.response_time_ms, c.dns_ms, c.tcp_ms, c.tls_ms, c.http_ms,
                   c.http_status, c.resolved_ip, c.message, c.checked_at
            FROM resources r
            LEFT JOIN checks c ON c.id = (
                SELECT id FROM checks WHERE resource_id=r.id ORDER BY checked_at DESC LIMIT 1
            )
            ORDER BY r.group_name, r.name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def summary() -> dict[str, Any]:
    resources = latest_resources()
    if not resources:
        return {"availability_index":0,"mode":"NO_INTERNET","total":0,"available":0,"problematic":0,"last_updated":0,"groups":{}}
    available = sum(1 for r in resources if r.get("status") == "OK")
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in resources:
        by_group.setdefault(row["group_name"], []).append(row)
    def ratio(name: str) -> float:
        group = by_group.get(name, [])
        if not group:
            return 1.0
        return sum(1 for r in group if r.get("status") == "OK") / len(group)
    internet = 1.0 if available > 0 else 0.0
    score = int(max(0, min(100, internet * 40 + ratio("RUSSIAN") * 20 + ratio("INTERNATIONAL") * 20 + ratio("CUSTOM") * 20)))
    total_ratio = available / len(resources)
    ru = ratio("RUSSIAN")
    intl = ratio("INTERNATIONAL")
    if total_ratio < 0.35:
        mode = "NO_INTERNET"
    elif intl < 0.30 and ru > 0.70:
        mode = "RESTRICTED_ACCESS"
    elif total_ratio < 0.70:
        mode = "PARTIAL_DEGRADATION"
    else:
        mode = "NORMAL"
    groups = {name: {"total":len(rows),"available":sum(1 for r in rows if r.get("status") == "OK")} for name, rows in by_group.items()}
    return {"availability_index":score,"mode":mode,"total":len(resources),"available":available,"problematic":len(resources)-available,"last_updated":max((r.get("checked_at") or 0) for r in resources),"groups":groups}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="NetWeather API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status":"ok","time":int(time.time())}

@app.get("/api/dashboard")
def dashboard():
    return {"summary":summary(),"resources":latest_resources()}

@app.get("/api/resources")
def list_resources():
    return latest_resources()

@app.post("/api/resources", dependencies=[Depends(require_token)])
def create_resource(payload: ResourceCreate):
    target = normalize_target(payload.target)
    now = int(time.time())
    with db() as conn:
        cur = conn.execute("INSERT INTO resources(name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at) VALUES(?,?,?,?,?,?,?,0)", (payload.name,target,payload.group_name.upper(),payload.interval_seconds,int(payload.enabled),now,now))
        resource_id = cur.lastrowid
    return {"id":resource_id}

@app.patch("/api/resources/{resource_id}", dependencies=[Depends(require_token)])
def patch_resource(resource_id: int, payload: ResourcePatch):
    values = payload.model_dump(exclude_none=True)
    if "target" in values:
        values["target"] = normalize_target(values["target"])
    if "group_name" in values:
        values["group_name"] = values["group_name"].upper()
    if "enabled" in values:
        values["enabled"] = int(values["enabled"])
    if not values:
        return {"ok":True}
    values["updated_at"] = int(time.time())
    columns = ", ".join(f"{key}=?" for key in values)
    with db() as conn:
        cur = conn.execute(f"UPDATE resources SET {columns} WHERE id=?", (*values.values(), resource_id))
    if cur.rowcount == 0:
        raise HTTPException(404, "Resource not found")
    return {"ok":True}

@app.delete("/api/resources/{resource_id}", dependencies=[Depends(require_token)])
def delete_resource(resource_id: int):
    with db() as conn:
        conn.execute("DELETE FROM checks WHERE resource_id=?", (resource_id,))
        cur = conn.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Resource not found")
    return {"ok":True}

@app.post("/api/resources/{resource_id}/check", dependencies=[Depends(require_token)])
async def manual_check(resource_id: int):
    return await check_resource(resource_id)

@app.post("/api/check-all", dependencies=[Depends(require_token)])
async def check_all():
    with db() as conn:
        rows = conn.execute("SELECT * FROM resources WHERE enabled=1").fetchall()
    results = await asyncio.gather(*(perform_check(row) for row in rows))
    for row, result in zip(rows, results):
        write_check(row["id"], result)
    return {"checked":len(rows)}

@app.get("/api/history")
def history(hours: int = 24):
    hours = max(1, min(hours, 720))
    since = int(time.time()) - hours * 3600
    with db() as conn:
        rows = conn.execute("SELECT resource_id, checked_at, status, response_time_ms FROM checks WHERE checked_at>=? ORDER BY checked_at ASC", (since,)).fetchall()
    buckets: dict[int, dict[str, Any]] = {}
    bucket_size = max(60, (hours * 3600) // 240)
    for row in rows:
        bucket = (row["checked_at"] // bucket_size) * bucket_size
        data = buckets.setdefault(bucket, {"timestamp":bucket,"total":0,"ok":0,"latency_sum":0})
        data["total"] += 1
        data["ok"] += int(row["status"] == "OK")
        data["latency_sum"] += row["response_time_ms"]
    return [{"timestamp":v["timestamp"],"availability":round(v["ok"] / v["total"] * 100) if v["total"] else 0,"avg_latency_ms":round(v["latency_sum"] / v["total"]) if v["total"] else 0} for v in buckets.values()]

if FRONTEND_DIR.exists():
    assets = FRONTEND_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = FRONTEND_DIR / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIR / "index.html")
