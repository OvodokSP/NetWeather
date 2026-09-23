from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import subprocess
import time
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import (
    ALERT_WEBHOOK_URL, ALLOW_PRIVATE_TARGETS, API_TOKEN, APP_VERSION, AUTH_REQUIRED, DEFAULT_INTERVAL,
    DEVICE_CODE_TTL_SECONDS, DEVICE_POLL_INTERVAL_SECONDS, DEVICE_TOKEN_MAX_AGE_SECONDS,
    DEVICE_AUTH_START_LIMIT, DEVICE_AUTH_START_WINDOW_SECONDS,
    DIAGNOSTIC_COOLDOWN_SECONDS, DIAGNOSTIC_MAX_POLL_ATTEMPTS, DIAGNOSTIC_POLL_SECONDS,
    DIAGNOSTIC_RESERVE_PERCENT, FRONTEND_DIR, GLOBALPING_BASE_URL, GLOBALPING_ENABLED,
    GLOBALPING_HOURLY_LIMIT, GLOBALPING_TOKEN, INTELLIGENCE_CACHE_SECONDS, IODA_BASE_URL,
    IODA_COUNTRY, IODA_ENABLED, KNOWN_GROUPS, OONI_BASE_URL, OONI_ENABLED, OONI_PROBE_COUNTRY,
    PUBLIC_ADD_LIMIT, PUBLIC_ADD_WINDOW_SECONDS, RUSSIA_CHECK_INTERVAL_SECONDS, RUSSIA_PROBE_COUNT, RUSSIA_PROBE_KEY,
    ResourceCreate, ResourcePatch, ClientProbeResult, ClientProbeRegistration, CatalogAddRequest, GroupCreate, GroupPatch,
    DeviceAuthorizationApprove, DeviceAuthorizationPoll, DeviceAuthorizationStart, OwnerLogin,
    SCHEDULER_ENABLED, SESSION_MAX_AGE, STARTED_AT, UI_PASSWORD,
    normalize_group, normalize_target,
)
from .database import (
    db, dual_summary, get_incidents, init_db, latest_resources, probe_statuses,
    register_probe, resource_groups, resource_matrix, seed_defaults, summary,
)
from .incidents import write_check
from .monitor import discover_target_metadata, perform_check, traceroute_to_resource
from .resource_catalog import CATALOG_BY_KEY, catalog_match, catalog_payload
from .availability import is_reachable
from .diagnostics import DiagnosticCoordinator, DiagnosticPriority, PersistentQuotaManager
from .providers import GlobalpingProvider
from .device_auth import (
    DeviceIdentity, approve_authorization, authenticate_device, list_devices,
    poll_authorization, revoke_device, start_authorization,
)
from .intelligence import IodaProvider, OoniProvider, StatuspageProvider
from .capabilities import capability_registry


SESSION_COOKIE = "netweather_owner"
_public_add_attempts: dict[str, list[float]] = {}
_device_auth_attempts: dict[str, list[float]] = {}
_diagnostic_request_lock = asyncio.Lock()
_quota = PersistentQuotaManager("globalping", GLOBALPING_HOURLY_LIMIT, DIAGNOSTIC_RESERVE_PERCENT)
_globalping = GlobalpingProvider(GLOBALPING_TOKEN, GLOBALPING_BASE_URL)
_diagnostics = DiagnosticCoordinator(_globalping, _quota, DIAGNOSTIC_COOLDOWN_SECONDS)
_ooni = OoniProvider(OONI_BASE_URL, OONI_PROBE_COUNTRY)
_ioda = IodaProvider(IODA_BASE_URL, IODA_COUNTRY)
_statuspage = StatuspageProvider()


def _owner_secret() -> str:
    return UI_PASSWORD or API_TOKEN


def _owner_cookie() -> str:
    secret = _owner_secret()
    if not secret:
        return ""
    digest = hmac.new(secret.encode("utf-8"), b"netweather-owner-session-v1", hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _is_owner(request: Request, authorization: str | None) -> bool:
    if API_TOKEN and authorization == f"Bearer {API_TOKEN}":
        return True
    cookie = request.cookies.get(SESSION_COOKIE, "")
    expected = _owner_cookie()
    return bool(cookie and expected and hmac.compare_digest(cookie, expected))


def require_token(request: Request, authorization: str | None = Header(default=None)) -> None:
    if not AUTH_REQUIRED:
        return
    if not _owner_secret():
        raise HTTPException(503, "Owner authentication is not configured")
    if not _is_owner(request, authorization):
        raise HTTPException(401, "Owner session required")


def require_monitoring_enabled() -> None:
    if not SCHEDULER_ENABLED:
        raise HTTPException(503, "Проверки и мониторинг на сайте временно остановлены")


def require_device(authorization: str | None = Header(default=None)) -> DeviceIdentity:
    if not AUTH_REQUIRED:
        return DeviceIdentity("LOCAL_DEVELOPMENT", "Local development")
    identity = authenticate_device(authorization, _owner_secret())
    if not identity:
        raise HTTPException(401, "Paired device token required")
    return identity


def _limit_public_add(request: Request, authorization: str | None) -> bool:
    """Return True for owner requests; rate-limit anonymous custom targets."""
    owner = not AUTH_REQUIRED or _is_owner(request, authorization)
    if owner:
        return True
    address = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    attempts = [stamp for stamp in _public_add_attempts.get(address, []) if now - stamp < PUBLIC_ADD_WINDOW_SECONDS]
    if len(attempts) >= PUBLIC_ADD_LIMIT:
        raise HTTPException(429, f"Можно добавить не более {PUBLIC_ADD_LIMIT} новых ресурсов в час")
    attempts.append(now)
    _public_add_attempts[address] = attempts
    return False


def _limit_device_auth_start(request: Request) -> None:
    address = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    attempts = [stamp for stamp in _device_auth_attempts.get(address, [])
                if now - stamp < DEVICE_AUTH_START_WINDOW_SECONDS]
    if len(attempts) >= max(1, DEVICE_AUTH_START_LIMIT):
        raise HTTPException(429, "Слишком много запросов кода подключения. Повторите позже.")
    attempts.append(now)
    _device_auth_attempts[address] = attempts


async def check_resource(resource_id: int):
    with db() as conn:
        resource = conn.execute("SELECT * FROM resources WHERE id=?", (resource_id,)).fetchone()
    if not resource:
        raise HTTPException(404, "Resource not found")
    payload = await perform_check(resource)
    write_check(resource_id, payload)
    return payload


async def run_scheduled(row) -> None:
    try:
        payload = await perform_check(row)
        notices = write_check(row["id"], payload)
    except Exception as exc:
        notices = write_check(row["id"], {
            "status":"UNKNOWN_ERROR","response_time_ms":0,"dns_ms":None,"tcp_ms":None,"tls_ms":None,
            "http_ms":None,"http_status":None,"resolved_ip":None,"tls_days_left":None,"final_url":row["target"],
            "location":None,"message":str(exc),
        })
    opened = next((notice for notice in notices if notice["event"] == "incident_opened"), None)
    if not opened:
        return
    if GLOBALPING_ENABLED:
        priority = DiagnosticPriority.NEW_DOWN if opened["kind"] == "DOWN" else DiagnosticPriority.DEGRADED
        await request_external_diagnostic(row["id"], priority)
    await refresh_external_intelligence(row["id"])


async def run_russia_check(row) -> None:
    """Measure the target from public Globalping probes located in Russia."""
    try:
        decision = _quota.consume(DiagnosticPriority.BACKGROUND, max(1, RUSSIA_PROBE_COUNT))
        if not decision.allowed:
            raise RuntimeError(f"Globalping quota: {decision.reason}")
        submission = await _globalping.submit_http(row["target"], probes=RUSSIA_PROBE_COUNT, locations=[{"country": "RU"}])
        result = None
        for _ in range(10):
            await asyncio.sleep(2)
            result = await _globalping.get_result(submission.external_id)
            if result.status in {"finished", "failed", "error"}:
                break
        summary = result.summary if result else {}
        classification = result.classification if result else None
        # An incomplete or mixed Globalping result is not evidence that the
        # resource is unavailable in Russia. Keep it explicitly unknown so
        # the UI cannot turn a provider timeout into a regional outage.
        status = (
            "OK" if classification == "OK"
            else "DNS_ERROR" if classification == "DNS_FAILURE"
            else "HTTP_ERROR" if classification in {"SERVICE_DOWN", "REGIONAL_OUTAGE"}
            else "UNKNOWN"
        )
        write_check(int(row["id"]), {
            "status": status, "response_time_ms": int(summary.get("median_latency_ms") or 0),
            "dns_ms": None, "tcp_ms": None, "tls_ms": None, "http_ms": None, "http_status": None,
            "resolved_ip": None, "tls_days_left": None, "final_url": row["target"], "location": "RU",
            "message": "РФ: публичные точки Globalping · " + (classification or (result.status if result else "нет результата")),
        }, probe_key=RUSSIA_PROBE_KEY, probe_scope="RUSSIA")
    except Exception as exc:
        write_check(int(row["id"]), {
            "status": "UNKNOWN", "response_time_ms": 0, "dns_ms": None, "tcp_ms": None,
            "tls_ms": None, "http_ms": None, "http_status": None, "resolved_ip": None,
            "tls_days_left": None, "final_url": row["target"], "location": "RU",
            "message": f"РФ Globalping: {str(exc)[:300]}",
        }, probe_key=RUSSIA_PROBE_KEY, probe_scope="RUSSIA")


async def russia_scheduler() -> None:
    while True:
        now = int(time.time())
        with db() as conn:
            rows = conn.execute("""SELECT r.* FROM resources r
              LEFT JOIN checks c ON c.id=(SELECT id FROM checks WHERE resource_id=r.id AND probe_scope='RUSSIA' ORDER BY checked_at DESC,id DESC LIMIT 1)
              WHERE r.enabled=1 AND (c.checked_at IS NULL OR ?>=c.checked_at+?) ORDER BY r.id LIMIT 30""",
              (now, max(300, RUSSIA_CHECK_INTERVAL_SECONDS))).fetchall()
        if rows and GLOBALPING_ENABLED:
            await asyncio.gather(*(run_russia_check(row) for row in rows))
        await asyncio.sleep(max(30, RUSSIA_CHECK_INTERVAL_SECONDS // 3))


def _store_evidence(resource_id: int | None, provider: str, scope_key: str, evidence, now: int) -> None:
    with db() as conn:
        conn.execute("""INSERT INTO external_evidence(
          resource_id,provider,scope_key,status,classification,confidence,summary_json,raw_json,fetched_at,expires_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""", (
            resource_id, provider, scope_key, evidence.status, evidence.classification, evidence.confidence,
            json.dumps(evidence.summary, ensure_ascii=False, separators=(",", ":")),
            "{}",
            now, now + max(300, INTELLIGENCE_CACHE_SECONDS),
        ))


async def refresh_external_intelligence(resource_id: int, force: bool = False) -> dict:
    with db() as conn:
        resource = conn.execute("SELECT id,target FROM resources WHERE id=?", (resource_id,)).fetchone()
    if not resource:
        raise HTTPException(404, "Resource not found")
    domain = (urlparse(resource["target"]).hostname or "").lower()
    now = int(time.time())
    result = {}
    if OONI_ENABLED and domain:
        with db() as conn:
            cached = conn.execute("""SELECT status,classification,confidence,summary_json,fetched_at,expires_at
              FROM external_evidence WHERE provider='ooni' AND scope_key=?
              ORDER BY fetched_at DESC,id DESC LIMIT 1""", (domain,)).fetchone()
        if cached and int(cached["expires_at"]) > now and not force:
            result["ooni"] = {**dict(cached), "summary": json.loads(cached["summary_json"] or "{}"), "cached": True}
        else:
            try:
                evidence = await _ooni.fetch(domain)
                _store_evidence(resource_id, "ooni", domain, evidence, now)
                result["ooni"] = {**evidence.summary, "status": evidence.status,
                                  "classification": evidence.classification, "confidence": evidence.confidence}
            except Exception as exc:
                result["ooni"] = {"status": "ERROR", "classification": "UNKNOWN", "error": str(exc)[:300]}
    if IODA_ENABLED:
        scope_key = f"country:{IODA_COUNTRY}"
        with db() as conn:
            cached = conn.execute("""SELECT status,classification,confidence,summary_json,fetched_at,expires_at
              FROM external_evidence WHERE provider='ioda' AND scope_key=?
              ORDER BY fetched_at DESC,id DESC LIMIT 1""", (scope_key,)).fetchone()
        if cached and int(cached["expires_at"]) > now and not force:
            result["ioda"] = {**dict(cached), "summary": json.loads(cached["summary_json"] or "{}"), "cached": True}
        else:
            try:
                evidence = await _ioda.fetch()
                _store_evidence(None, "ioda", scope_key, evidence, now)
                result["ioda"] = {**evidence.summary, "status": evidence.status,
                                  "classification": evidence.classification, "confidence": evidence.confidence}
            except Exception as exc:
                result["ioda"] = {"status": "ERROR", "classification": "UNKNOWN", "error": str(exc)[:300]}
    try:
        with db() as conn:
            cached = conn.execute("""SELECT status,classification,confidence,summary_json,fetched_at,expires_at
              FROM external_evidence WHERE provider='statuspage' AND scope_key=?
              ORDER BY fetched_at DESC,id DESC LIMIT 1""", (domain,)).fetchone()
        if cached and int(cached["expires_at"]) > now and not force:
            result["statuspage"] = {**dict(cached), "summary": json.loads(cached["summary_json"] or "{}"), "cached": True}
        else:
            status_evidence = await _statuspage.fetch(resource["target"])
            if status_evidence:
                _store_evidence(resource_id, "statuspage", domain, status_evidence, now)
                result["statuspage"] = {**status_evidence.summary, "status": status_evidence.status,
                                         "classification": status_evidence.classification,
                                         "confidence": status_evidence.confidence}
    except Exception as exc:
        result["statuspage"] = {"status": "ERROR", "classification": "UNKNOWN", "error": str(exc)[:300]}
    return result


async def poll_external_diagnostics_once() -> int:
    now = int(time.time())
    with db() as conn:
        jobs = conn.execute("""SELECT id,external_id,poll_attempts FROM diagnostic_jobs
          WHERE provider='globalping' AND external_id IS NOT NULL
            AND status IN ('queued','in-progress') AND COALESCE(next_poll_at,0)<=?
          ORDER BY priority,created_at LIMIT 20""", (now,)).fetchall()
    completed = 0
    for job in jobs:
        attempts = int(job["poll_attempts"] or 0) + 1
        try:
            result = await _globalping.get_result(job["external_id"])
            terminal = result.status in {"finished", "failed", "error"}
            with db() as conn:
                conn.execute("""UPDATE diagnostic_jobs SET status=?,classification=?,confidence=?,
                  result_summary_json=?,raw_json='{}',poll_attempts=?,next_poll_at=?,completed_at=?,updated_at=?,error=NULL
                  WHERE id=?""", (
                    result.status, result.classification, result.confidence,
                    json.dumps(result.summary, ensure_ascii=False, separators=(",", ":")),
                    attempts, None if terminal else now + max(3, DIAGNOSTIC_POLL_SECONDS),
                    now if terminal else None, now, job["id"],
                ))
            completed += int(terminal)
        except Exception as exc:
            terminal = attempts >= max(1, DIAGNOSTIC_MAX_POLL_ATTEMPTS)
            with db() as conn:
                conn.execute("""UPDATE diagnostic_jobs SET status=?,poll_attempts=?,next_poll_at=?,updated_at=?,error=?
                  WHERE id=?""", (
                    "failed" if terminal else "in-progress", attempts,
                    None if terminal else now + max(3, DIAGNOSTIC_POLL_SECONDS), now, str(exc)[:500], job["id"],
                ))
    return completed


async def diagnostic_poller() -> None:
    while True:
        await poll_external_diagnostics_once()
        await asyncio.sleep(max(3, DIAGNOSTIC_POLL_SECONDS))


async def scheduler() -> None:
    while True:
        now = int(time.time())
        with db() as conn:
            due = conn.execute(
                "SELECT * FROM resources WHERE enabled=1 AND (? - last_checked_at)>=interval_seconds ORDER BY last_checked_at ASC LIMIT 25",
                (now,),
            ).fetchall()
        if due:
            await asyncio.gather(*(run_scheduled(row) for row in due))
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if AUTH_REQUIRED and not _owner_secret():
        raise RuntimeError("Owner authentication secret is required")
    init_db()
    seed_defaults()
    task = asyncio.create_task(scheduler()) if SCHEDULER_ENABLED else None
    diagnostic_task = asyncio.create_task(diagnostic_poller()) if SCHEDULER_ENABLED and GLOBALPING_ENABLED else None
    russia_task = asyncio.create_task(russia_scheduler()) if SCHEDULER_ENABLED and GLOBALPING_ENABLED else None
    yield
    for active_task in (task, diagnostic_task, russia_task):
        if active_task:
            active_task.cancel()
            try:
                await active_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="NetWeather API", version=APP_VERSION, lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"status":"ok","version":APP_VERSION,"time":int(time.time()),"uptime_seconds":int(time.time())-STARTED_AT}


@app.get("/api/system")
def system_info():
    with db() as conn:
        resources=conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        checks=conn.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
        incidents=conn.execute("SELECT COUNT(*) FROM incidents WHERE closed_at IS NULL").fetchone()[0]
    traceroute_available=subprocess.call(["sh","-c","command -v traceroute >/dev/null 2>&1"])==0
    return {"version":APP_VERSION,"started_at":STARTED_AT,"uptime_seconds":int(time.time())-STARTED_AT,"resources":resources,
      "checks":checks,"active_incidents":incidents,"database":"ok","traceroute_available":traceroute_available,
      "webhook_configured":bool(ALERT_WEBHOOK_URL),"private_targets_allowed":ALLOW_PRIVATE_TARGETS,
      "default_interval_seconds":DEFAULT_INTERVAL,"scheduler_enabled":SCHEDULER_ENABLED,"monitoring_paused":not SCHEDULER_ENABLED,
      "auth_required":AUTH_REQUIRED,"globalping_enabled":GLOBALPING_ENABLED and SCHEDULER_ENABLED,
      "ooni_enabled":OONI_ENABLED and SCHEDULER_ENABLED,"ioda_enabled":IODA_ENABLED and SCHEDULER_ENABLED,"diagnostic_quota":_quota.status()}


@app.get("/api/capabilities")
def capabilities(request: Request, authorization: str | None = Header(default=None)):
    return capability_registry(owner=not AUTH_REQUIRED or _is_owner(request, authorization),
                               globalping_enabled=GLOBALPING_ENABLED and SCHEDULER_ENABLED)


@app.get("/api/auth/verify", dependencies=[Depends(require_token)])
def verify_token():
    return {"ok":True}


@app.get("/api/session")
def session_status(request: Request, authorization: str | None = Header(default=None)):
    return {
        "authenticated": True if not AUTH_REQUIRED else _is_owner(request, authorization),
        "auth_required": AUTH_REQUIRED,
        "password_configured": bool(_owner_secret()),
    }


@app.post("/api/session/login")
def session_login(payload: OwnerLogin, response: Response):
    if not AUTH_REQUIRED:
        return {"ok":True,"open_access":True,"expires_in":0}
    secret = _owner_secret()
    if not secret:
        raise HTTPException(503, "Owner authentication is not configured")
    if not hmac.compare_digest(payload.password, secret):
        raise HTTPException(401, "Неверный пароль владельца")
    response.set_cookie(
        SESSION_COOKIE,
        _owner_cookie(),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"ok":True,"expires_in":SESSION_MAX_AGE}


@app.post("/api/session/logout")
def session_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok":True}


@app.post("/api/v1/device-auth/start")
def device_auth_start(payload: DeviceAuthorizationStart, request: Request):
    if not _owner_secret():
        raise HTTPException(503, "Device authorization is not configured")
    _limit_device_auth_start(request)
    return start_authorization(
        device_id=payload.device_id, device_name=payload.device_name,
        app_version=payload.app_version, server_secret=_owner_secret(),
        ttl_seconds=DEVICE_CODE_TTL_SECONDS, poll_interval_seconds=DEVICE_POLL_INTERVAL_SECONDS,
    )


@app.post("/api/v1/device-auth/poll")
def device_auth_poll(payload: DeviceAuthorizationPoll):
    if not _owner_secret():
        raise HTTPException(503, "Device authorization is not configured")
    result = poll_authorization(
        payload.session_id, payload.poll_secret, _owner_secret(), DEVICE_TOKEN_MAX_AGE_SECONDS,
    )
    if result["status"] == "invalid":
        raise HTTPException(404, "Authorization session not found")
    return result


@app.post("/api/device-auth/approve", dependencies=[Depends(require_token)])
def device_auth_approve(payload: DeviceAuthorizationApprove):
    approved = approve_authorization(payload.user_code, _owner_secret())
    if not approved:
        raise HTTPException(404, "Код не найден или истёк")
    return {"ok": True, **approved}


@app.get("/api/devices", dependencies=[Depends(require_token)])
def devices_list():
    return list_devices()


@app.delete("/api/devices/{device_id}", dependencies=[Depends(require_token)])
def device_revoke(device_id: str):
    if not revoke_device(device_id):
        raise HTTPException(404, "Device not found")
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard():
    return {
        "summary": dual_summary(),
        "legacy_summary": summary(),
        "resources": resource_matrix(),
        "incidents": get_incidents(True,20),
        "probes": probe_statuses(),
    }


@app.get("/api/probes")
def probes():
    return probe_statuses()


@app.get("/api/groups")
def groups():
    rows = resource_groups()
    return [{"id":r["group_key"],"title":r["title"],"color":r["color"],"sort_order":r["sort_order"],"resource_count":r["resource_count"]} for r in rows]


@app.post("/api/groups", dependencies=[Depends(require_token)])
def create_group(payload: GroupCreate):
    key = normalize_group(payload.key or payload.title)
    now = int(time.time())
    with db() as conn:
        if conn.execute("SELECT 1 FROM resource_groups WHERE group_key=?", (key,)).fetchone():
            raise HTTPException(409, "Группа уже существует")
        conn.execute("""INSERT INTO resource_groups(group_key,title,color,sort_order,created_at,updated_at)
          VALUES(?,?,?,?,?,?)""",(key,payload.title.strip(),payload.color,100,now,now))
    return {"id":key,"title":payload.title.strip(),"color":payload.color}


@app.patch("/api/groups/{group_key}", dependencies=[Depends(require_token)])
def patch_group(group_key: str, payload: GroupPatch):
    values = payload.model_dump(exclude_none=True)
    if not values:
        return {"ok":True}
    values["updated_at"] = int(time.time())
    columns = ", ".join(f"{k}=?" for k in values)
    with db() as conn:
        cur = conn.execute(f"UPDATE resource_groups SET {columns} WHERE group_key=?", (*values.values(), group_key))
    if cur.rowcount == 0:
        raise HTTPException(404, "Группа не найдена")
    return {"ok":True}


@app.delete("/api/groups/{group_key}", dependencies=[Depends(require_token)])
def delete_group(group_key: str):
    if group_key == "CUSTOM":
        raise HTTPException(400, "Системную группу CUSTOM удалить нельзя")
    now = int(time.time())
    with db() as conn:
        conn.execute("UPDATE resources SET group_name='CUSTOM',updated_at=? WHERE group_name=?", (now,group_key))
        cur = conn.execute("DELETE FROM resource_groups WHERE group_key=?", (group_key,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Группа не найдена")
    return {"ok":True,"reassigned_to":"CUSTOM"}


@app.get("/api/target-meta", dependencies=[Depends(require_monitoring_enabled)])
async def target_metadata(target:str=Query(min_length=1,max_length=2048)):
    return await discover_target_metadata(target)


def _ensure_resource_group(conn, group_name:str, now:int) -> None:
    conn.execute("""INSERT INTO resource_groups(group_key,title,color,sort_order,created_at,updated_at)
      VALUES(?,?,?,?,?,?) ON CONFLICT(group_key) DO NOTHING""",
      (group_name,KNOWN_GROUPS.get(group_name,group_name),"#8A96A3",100,now,now))


def _insert_catalog_resource(conn, item, now:int, *, interval_seconds:int=DEFAULT_INTERVAL,
                             expected_status_min:int=200, expected_status_max:int=399,
                             slow_threshold_ms:int=1500, failure_threshold:int=2,
                             alerts_enabled:bool=True, enabled:bool=True) -> tuple[int,bool]:
    existing=conn.execute("SELECT id FROM resources WHERE catalog_key=? LIMIT 1",(item.key,)).fetchone()
    if existing:
        return int(existing["id"]),False
    _ensure_resource_group(conn,item.group_key,now)
    cur=conn.execute("""INSERT INTO resources(
      name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at,
      expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,alerts_enabled,
      last_success_at,last_failure_at,catalog_key,allow_http_rejected
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (item.name,normalize_target(item.target),item.group_key,interval_seconds,int(enabled),now,now,0,
     expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,int(alerts_enabled),0,0,item.key,1))
    return int(cur.lastrowid),True


def _target_key(value:str) -> str:
    from urllib.parse import urlparse
    target=normalize_target(value)
    parsed=urlparse(target)
    host=(parsed.hostname or "").lower().rstrip(".")
    port=f":{parsed.port}" if parsed.port else ""
    path=(parsed.path or "/").rstrip("/") or "/"
    query=f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{host}{port}{path}{query}"


@app.get("/api/resource-catalog")
def resource_catalog():
    with db() as conn:
        existing={row["catalog_key"] for row in conn.execute(
            "SELECT catalog_key FROM resources WHERE catalog_key IS NOT NULL AND catalog_key<>''"
        ).fetchall()}
    return catalog_payload(existing)


@app.get("/api/resource-catalog/match")
def resource_catalog_match(target:str=Query(min_length=1,max_length=2048)):
    match=catalog_match(target)
    if not match:
        return {"matched":False}
    with db() as conn:
        row=conn.execute("SELECT id FROM resources WHERE catalog_key=? LIMIT 1",(match.key,)).fetchone()
    return {
        "matched":True,
        "resource":match.public(),
        "already_added":bool(row),
        "existing_resource_id":int(row["id"]) if row else None,
    }


@app.post("/api/resource-catalog/add")
def add_catalog_resources(payload:CatalogAddRequest):
    keys=list(dict.fromkeys(payload.resource_keys))
    unknown=[key for key in keys if key not in CATALOG_BY_KEY]
    if unknown:
        raise HTTPException(400,"Unknown catalog resource: "+", ".join(unknown))
    added=[]
    existing=[]
    now=int(time.time())
    with db() as conn:
        for key in keys:
            item=CATALOG_BY_KEY[key]
            resource_id,created=_insert_catalog_resource(conn,item,now)
            target=added if created else existing
            target.append({"id":resource_id,"key":item.key,"name":item.name,"group_key":item.group_key})
    return {"added":added,"existing":existing,"requested":len(keys)}


@app.get("/api/resources")
def list_resources():
    return resource_matrix()


@app.get("/api/resources/{resource_id}")
def resource_details(resource_id:int):
    rows=[r for r in resource_matrix() if r["id"]==resource_id]
    if not rows: raise HTTPException(404,"Resource not found")
    with db() as conn:
        checks=conn.execute("SELECT * FROM checks WHERE resource_id=? ORDER BY checked_at DESC,id DESC LIMIT 30",(resource_id,)).fetchall()
        cutoff = int(time.time()) - 365 * 86400
        timeline = []
        for row in conn.execute("""SELECT id,provider,status,classification,confidence,result_summary_json,created_at,completed_at
          FROM diagnostic_jobs WHERE resource_id=? AND COALESCE(completed_at,created_at)>=?
          ORDER BY COALESCE(completed_at,created_at) DESC,id DESC LIMIT 120""", (resource_id, cutoff)):
            timeline.append({"id":f"diagnostic:{row['id']}","type":"diagnostic","time":row["completed_at"] or row["created_at"],
              "source":row["provider"],"status":row["status"],"classification":row["classification"],
              "confidence":row["confidence"],"summary":json.loads(row["result_summary_json"] or "{}")})
        for row in conn.execute("""SELECT id,provider,status,classification,confidence,summary_json,fetched_at
          FROM external_evidence WHERE (resource_id=? OR resource_id IS NULL) AND fetched_at>=?
          ORDER BY fetched_at DESC,id DESC LIMIT 120""", (resource_id, cutoff)):
            timeline.append({"id":f"evidence:{row['id']}","type":"evidence","time":row["fetched_at"],
              "source":row["provider"],"status":row["status"],"classification":row["classification"],
              "confidence":row["confidence"],"summary":json.loads(row["summary_json"] or "{}")})
        for row in conn.execute("""SELECT id,kind,severity,opened_at,closed_at,message FROM incidents
          WHERE resource_id=? AND (opened_at>=? OR closed_at>=?) ORDER BY opened_at DESC,id DESC LIMIT 120""",
          (resource_id, cutoff, cutoff)):
            timeline.append({"id":f"incident:{row['id']}:opened","type":"incident_opened","time":row["opened_at"],
              "source":"incident","status":"OPENED","classification":row["kind"],"confidence":None,
              "summary":{"severity":row["severity"],"message":row["message"]}})
            if row["closed_at"] and row["closed_at"] >= cutoff:
                timeline.append({"id":f"incident:{row['id']}:closed","type":"incident_closed","time":row["closed_at"],
                  "source":"incident","status":"CLOSED","classification":row["kind"],"confidence":None,
                  "summary":{"severity":row["severity"],"message":row["message"]}})
        status_rows = conn.execute("""SELECT checked_at,status,probe_scope,message FROM checks
          WHERE resource_id=? AND checked_at>=? ORDER BY checked_at,id LIMIT 1000""", (resource_id, cutoff)).fetchall()
        previous = {}
        for row in status_rows:
            scope = row["probe_scope"]
            old = previous.get(scope)
            if old and old["status"] != row["status"] and is_reachable(old["status"]) != is_reachable(row["status"]):
                timeline.append({"id":f"check:{resource_id}:{row['checked_at']}:{scope}","type":"status_change",
                  "time":row["checked_at"],"source":scope,"status":row["status"],"classification":row["status"],
                  "confidence":None,"summary":{"previous_status":old["status"],"message":row["message"]}})
            previous[scope] = row
    timeline.sort(key=lambda item:(int(item["time"] or 0),item["id"]),reverse=True)
    return {"resource":rows[0],"checks":[dict(r) for r in checks],
            "incidents":[i for i in get_incidents(False,200) if i["resource_id"]==resource_id][:20],
            "timeline":timeline[:100]}


@app.post("/api/resources")
def create_resource(payload:ResourceCreate, request:Request, authorization:str|None=Header(default=None)):
    target=normalize_target(payload.target)
    owner = not AUTH_REQUIRED or _is_owner(request, authorization)
    interval_seconds = payload.interval_seconds if owner else DEFAULT_INTERVAL
    expected_status_min = payload.expected_status_min if owner else 200
    expected_status_max = payload.expected_status_max if owner else 399
    slow_threshold_ms = payload.slow_threshold_ms if owner else 1500
    failure_threshold = payload.failure_threshold if owner else 2
    alerts_enabled = payload.alerts_enabled if owner else False
    enabled = payload.enabled if owner else True
    if expected_status_min>expected_status_max:
        raise HTTPException(400,"Expected status min must be <= max")
    now=int(time.time())
    match=catalog_match(target)
    with db() as conn:
        if match:
            existing=conn.execute("SELECT id FROM resources WHERE catalog_key=? LIMIT 1",(match.key,)).fetchone()
            if not existing and not owner:
                _limit_public_add(request, authorization)
            resource_id,created=_insert_catalog_resource(
                conn,match,now,
                interval_seconds=interval_seconds,
                expected_status_min=expected_status_min,
                expected_status_max=expected_status_max,
                slow_threshold_ms=slow_threshold_ms,
                failure_threshold=failure_threshold,
                alerts_enabled=alerts_enabled,
                enabled=enabled,
            )
            return {
                "id":resource_id,
                "created":created,
                "used_catalog":True,
                "catalog_match":match.public(),
                "already_exists":not created,
            }
        target_key=_target_key(target)
        for row in conn.execute("SELECT id,target FROM resources").fetchall():
            try:
                if _target_key(row["target"])==target_key:
                    return {"id":int(row["id"]),"created":False,"used_catalog":False,"already_exists":True}
            except HTTPException:
                continue
        group_name=normalize_group(payload.group_name)
        if not owner and group_name not in KNOWN_GROUPS:
            group_name="CUSTOM"
        if not owner:
            _limit_public_add(request, authorization)
        _ensure_resource_group(conn,group_name,now)
        cur=conn.execute("""INSERT INTO resources(
          name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at,
          expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,alerts_enabled,
          last_success_at,last_failure_at,catalog_key,allow_http_rejected
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,0)""",
        (payload.name,target,group_name,interval_seconds,int(enabled),now,now,0,
         expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,
         int(alerts_enabled),0,0))
    return {"id":int(cur.lastrowid),"created":True,"used_catalog":False,"already_exists":False}


@app.patch("/api/resources/{resource_id}", dependencies=[Depends(require_token)])
def patch_resource(resource_id:int,payload:ResourcePatch):
    values=payload.model_dump(exclude_none=True)
    if "target" in values:
        values["target"]=normalize_target(values["target"])
        match=catalog_match(values["target"])
        if match:
            with db() as conn:
                existing=conn.execute("SELECT id FROM resources WHERE catalog_key=? AND id<>? LIMIT 1",(match.key,resource_id)).fetchone()
            if existing:
                raise HTTPException(409,f"Этот ресурс уже добавлен из каталога: {match.name}")
            values["target"]=normalize_target(match.target)
            values["name"]=match.name
            values["group_name"]=match.group_key
            values["catalog_key"]=match.key
            values["allow_http_rejected"]=1
        else:
            values["catalog_key"]=None
            values["allow_http_rejected"]=0
    if "group_name" in values:
        values["group_name"]=normalize_group(values["group_name"])
        now_group=int(time.time())
        with db() as conn:
            conn.execute("""INSERT INTO resource_groups(group_key,title,color,sort_order,created_at,updated_at)
              VALUES(?,?,?,?,?,?) ON CONFLICT(group_key) DO NOTHING""",
              (values["group_name"],KNOWN_GROUPS.get(values["group_name"],values["group_name"]),"#8A96A3",100,now_group,now_group))
    for key in ("enabled","alerts_enabled"):
        if key in values: values[key]=int(values[key])
    if "expected_status_min" in values or "expected_status_max" in values:
        with db() as conn: row=conn.execute("SELECT expected_status_min,expected_status_max FROM resources WHERE id=?",(resource_id,)).fetchone()
        if not row: raise HTTPException(404,"Resource not found")
        lo=values.get("expected_status_min",row["expected_status_min"]); hi=values.get("expected_status_max",row["expected_status_max"])
        if lo>hi: raise HTTPException(400,"Expected status min must be <= max")
    if not values: return {"ok":True}
    values["updated_at"]=int(time.time()); columns=", ".join(f"{k}=?" for k in values)
    with db() as conn: cur=conn.execute(f"UPDATE resources SET {columns} WHERE id=?",(*values.values(),resource_id))
    if cur.rowcount==0: raise HTTPException(404,"Resource not found")
    return {"ok":True}


@app.delete("/api/resources/{resource_id}", dependencies=[Depends(require_token)])
def delete_resource(resource_id:int):
    with db() as conn: cur=conn.execute("DELETE FROM resources WHERE id=?",(resource_id,))
    if cur.rowcount==0: raise HTTPException(404,"Resource not found")
    return {"ok":True}


@app.post("/api/resources/{resource_id}/check", dependencies=[Depends(require_token), Depends(require_monitoring_enabled)])
async def manual_check(resource_id:int):
    payload = await check_resource(resource_id)
    payload["external_diagnostic"] = None
    if GLOBALPING_ENABLED and not is_reachable(payload["status"]):
        payload["external_diagnostic"] = await request_external_diagnostic(resource_id, DiagnosticPriority.MANUAL)
    return payload


@app.post("/api/resources/{resource_id}/trace", dependencies=[Depends(require_token), Depends(require_monitoring_enabled)])
async def trace_resource(resource_id:int): return await traceroute_to_resource(resource_id)


@app.get("/api/v1/client-probe/resources", dependencies=[Depends(require_monitoring_enabled)])
def client_probe_resources(device: DeviceIdentity = Depends(require_device)):
    with db() as conn:
        rows = conn.execute("""SELECT id,name,target,group_name,expected_status_min,expected_status_max
          FROM resources WHERE enabled=1 ORDER BY group_name,name""").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/client-probe/result", dependencies=[Depends(require_monitoring_enabled)])
def client_probe_result(payload: ClientProbeResult, probe: ClientProbeRegistration,
                        device: DeviceIdentity = Depends(require_device)):
    probe_key = probe.probe_key if device.device_id == "LOCAL_DEVELOPMENT" else device.device_id
    probe_name = probe.name if device.device_id == "LOCAL_DEVELOPMENT" else device.name
    register_probe(probe_key, probe_name, "USER", probe.app_version, "dns,tcp,tls,http")
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM resources WHERE id=?", (payload.resource_id,)).fetchone()
    if not exists:
        raise HTTPException(404, "Resource not found")
    data = payload.model_dump()
    data.update({"tls_days_left":None,"final_url":None,"location":None})
    write_check(payload.resource_id, data, probe_key=probe_key, probe_scope="USER")
    return {"ok":True}


async def request_external_diagnostic(resource_id: int, priority: DiagnosticPriority):
    async with _diagnostic_request_lock:
        with db() as conn:
            resource = conn.execute("SELECT id,target FROM resources WHERE id=?", (resource_id,)).fetchone()
            if not resource:
                raise HTTPException(404, "Resource not found")
            now = int(time.time())
            recent = conn.execute("""SELECT id,external_id,status,error FROM diagnostic_jobs
              WHERE resource_id=? AND provider='globalping' AND (
                status IN ('queued','in-progress','submitting') OR created_at>?
              ) ORDER BY created_at DESC,id DESC LIMIT 1""", (
                resource_id, now - _diagnostics.cooldown_seconds,
            )).fetchone()
        if recent:
            return {"job_id":recent["id"],"provider":"globalping","external_id":recent["external_id"],
                    "status":recent["status"],"error":recent["error"],"deduplicated":True}
        try:
            result = await _diagnostics.request(resource_id, resource["target"], priority)
            status, external_id, error = result.status, result.external_id, None
        except Exception as exc:
            status, external_id, error = "rejected", None, str(exc)[:500]
        with db() as conn:
            job_id = conn.execute("""INSERT INTO diagnostic_jobs(
              resource_id,provider,external_id,priority,status,created_at,updated_at,error
            ) VALUES(?,?,?,?,?,?,?,?)""", (resource_id,"globalping",external_id,int(priority),status,now,now,error)).lastrowid
            if external_id:
                conn.execute("UPDATE diagnostic_jobs SET next_poll_at=? WHERE id=?", (now + max(3, DIAGNOSTIC_POLL_SECONDS), job_id))
        return {"job_id":job_id,"provider":"globalping","external_id":external_id,"status":status,"error":error}


@app.get("/api/diagnostics/status")
def diagnostic_status():
    return {"provider":"globalping","enabled":GLOBALPING_ENABLED and SCHEDULER_ENABLED,"quota":_quota.status(),
            "reserve_percent":DIAGNOSTIC_RESERVE_PERCENT,"cooldown_seconds":DIAGNOSTIC_COOLDOWN_SECONDS,
            "poll_seconds":DIAGNOSTIC_POLL_SECONDS,"ooni_enabled":OONI_ENABLED,"ioda_enabled":IODA_ENABLED}


@app.post("/api/resources/{resource_id}/diagnose", dependencies=[Depends(require_token), Depends(require_monitoring_enabled)])
async def diagnose_resource(resource_id:int):
    if not GLOBALPING_ENABLED:
        raise HTTPException(503, "External diagnostics provider is disabled")
    diagnostic = await request_external_diagnostic(resource_id, DiagnosticPriority.MANUAL)
    diagnostic["intelligence"] = await refresh_external_intelligence(resource_id, force=True)
    return diagnostic


@app.post("/api/resources/{resource_id}/intelligence", dependencies=[Depends(require_token), Depends(require_monitoring_enabled)])
async def refresh_resource_intelligence(resource_id: int):
    return await refresh_external_intelligence(resource_id, force=True)


@app.get("/api/resources/{resource_id}/diagnostics")
def resource_diagnostics(resource_id:int):
    with db() as conn:
        rows = conn.execute("SELECT * FROM diagnostic_jobs WHERE resource_id=? ORDER BY created_at DESC LIMIT 20", (resource_id,)).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/trace-tasks/{task_id}")
def trace_task(task_id:int):
    with db() as conn:
        row = conn.execute("SELECT * FROM diagnostic_jobs WHERE id=?", (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Diagnostic task not found")
    return dict(row)


@app.post("/api/check-all", dependencies=[Depends(require_token), Depends(require_monitoring_enabled)])
async def check_all():
    with db() as conn: rows=conn.execute("SELECT * FROM resources WHERE enabled=1").fetchall()
    results=await asyncio.gather(*(perform_check(row) for row in rows))
    for row,result in zip(rows,results): write_check(row["id"],result)
    return {"checked":len(rows),"ok":sum(1 for r in results if is_reachable(r["status"])),"failed":sum(1 for r in results if not is_reachable(r["status"]))}


@app.get("/api/incidents")
def incidents(active:bool=Query(default=False),limit:int=Query(default=100,ge=1,le=500)):
    return get_incidents(active,limit)


@app.post("/api/incidents/{incident_id}/ack", dependencies=[Depends(require_token)])
def acknowledge_incident(incident_id:int):
    with db() as conn: cur=conn.execute("UPDATE incidents SET acknowledged_at=? WHERE id=?",(int(time.time()),incident_id))
    if cur.rowcount==0: raise HTTPException(404,"Incident not found")
    return {"ok":True}


@app.post("/api/incidents/ack-all", dependencies=[Depends(require_token)])
def acknowledge_all_incidents():
    now=int(time.time())
    with db() as conn:
        cur=conn.execute("UPDATE incidents SET acknowledged_at=? WHERE acknowledged_at IS NULL",(now,))
    return {"ok":True,"acknowledged":cur.rowcount,"acknowledged_at":now}


@app.get("/api/realtime")
def realtime(minutes:int=Query(default=60,ge=5,le=10080), scope:str=Query(default="EXTERNAL")):
    scope=scope.upper()
    scope_key={"EXTERNAL":"GLOBAL","DOMESTIC":"RUSSIA"}.get(scope,scope)
    if scope_key not in {"GLOBAL","RUSSIA","USER"}:
        raise HTTPException(400,"scope must be EXTERNAL, DOMESTIC or USER")
    now=int(time.time())
    since=now-minutes*60
    bucket=max(30,(minutes*60)//240)
    availability_window=3600
    with db() as conn:
        resources=[dict(r) for r in conn.execute(
            "SELECT id,name,target,group_name FROM resources WHERE enabled=1 ORDER BY name"
        ).fetchall()]
        rows=conn.execute("""SELECT resource_id,checked_at,status,response_time_ms,dns_ms,tcp_ms,tls_ms,http_ms,http_status
          FROM checks WHERE checked_at>=? AND probe_scope=? ORDER BY checked_at ASC,id ASC""",
          (since-availability_window,scope_key)).fetchall()
        stats24=conn.execute("""SELECT resource_id,
          COUNT(*) total,
          SUM(CASE WHEN status IN ('OK','HTTP_REJECTED') THEN 1 ELSE 0 END) ok,
          AVG(response_time_ms) avg_latency,
          MAX(checked_at) last_checked
          FROM checks WHERE checked_at>=? AND probe_scope=? GROUP BY resource_id""",
          (now-86400,scope_key)).fetchall()
    stats={int(r["resource_id"]):dict(r) for r in stats24}
    by_resource={}
    for row in rows:
        rid=int(row["resource_id"])
        b=(int(row["checked_at"])//bucket)*bucket
        target=by_resource.setdefault(rid,{})
        point=target.setdefault(b,{"timestamp":b,"total":0,"ok":0,"latency_sum":0,"latency_count":0})
        point["total"]+=1
        point["ok"]+=int(is_reachable(row["status"]))
        if row["response_time_ms"] is not None:
            point["latency_sum"]+=int(row["response_time_ms"])
            point["latency_count"]+=1
    result=[]
    for resource in resources:
        rid=int(resource["id"])
        ordered=sorted(by_resource.get(rid,{}).values(),key=lambda x:x["timestamp"])
        points=[]
        for idx,p in enumerate(ordered):
            if p["timestamp"] < since:
                continue
            window_start=p["timestamp"]-availability_window
            rolling_total=0
            rolling_ok=0
            j=idx
            while j>=0 and ordered[j]["timestamp"]>=window_start:
                rolling_total+=ordered[j]["total"]
                rolling_ok+=ordered[j]["ok"]
                j-=1
            points.append({
                "timestamp":p["timestamp"],
                "availability":round(rolling_ok/rolling_total*100,1) if rolling_total else None,
                "latency_ms":round(p["latency_sum"]/p["latency_count"]) if p["latency_count"] else None,
                "checks":p["total"],
            })
        st=stats.get(rid,{})
        total=int(st.get("total") or 0)
        ok=int(st.get("ok") or 0)
        result.append({
            **resource,
            "availability_24h":round(ok/total*100,2) if total else None,
            "avg_latency_24h_ms":round(st.get("avg_latency")) if st.get("avg_latency") is not None else None,
            "last_checked_at":st.get("last_checked"),
            "points":points,
        })
    return {
        "scope":scope,"minutes":minutes,"bucket_seconds":bucket,
        "availability_window_seconds":availability_window,
        "from":since,"to":now,"resources":result,
    }


@app.get("/api/events")
def recent_events(limit:int=Query(default=30,ge=1,le=100)):
    with db() as conn:
        incidents=[dict(r) for r in conn.execute("""SELECT i.id,i.resource_id,i.kind,i.severity,i.opened_at,i.closed_at,i.acknowledged_at,i.message,
          r.name resource_name FROM incidents i JOIN resources r ON r.id=i.resource_id
          ORDER BY COALESCE(i.closed_at,i.opened_at) DESC LIMIT ?""",(limit,)).fetchall()]
        checks=[dict(r) for r in conn.execute("""SELECT c.id,c.resource_id,c.checked_at,c.status,c.response_time_ms,c.http_status,c.message,c.probe_scope,
          r.name resource_name FROM checks c JOIN resources r ON r.id=c.resource_id
          ORDER BY c.checked_at DESC,c.id DESC LIMIT ?""",(max(limit*8,80),)).fetchall()]
    events=[]
    for inc in incidents:
        events.append({
            "type":"incident_closed" if inc["closed_at"] else "incident_open",
            "time":inc["closed_at"] or inc["opened_at"],
            "incident_id":inc["id"],
            "acknowledged_at":inc["acknowledged_at"],
            "resource_id":inc["resource_id"],
            "resource_name":inc["resource_name"],
            "severity":inc["severity"],
            "title":("Восстановление: " if inc["closed_at"] else "Инцидент: ")+inc["resource_name"],
            "message":inc["message"],
            "kind":inc["kind"],
        })
    previous={}
    for row in reversed(checks):
        key=(row["resource_id"],row["probe_scope"])
        old=previous.get(key)
        if (
            old is not None
            and old != row["status"]
            and is_reachable(old) != is_reachable(row["status"])
        ):
            events.append({
                "type":"status_change",
                "time":row["checked_at"],
                "resource_id":row["resource_id"],
                "resource_name":row["resource_name"],
                "severity":"info" if is_reachable(row["status"]) else "warning",
                "title":("Восстановление " if is_reachable(row["status"]) else "Изменение состояния ")+row["resource_name"],
                "message":f"{row['probe_scope']}: {old} → {row['status']} · {row['message'] or ''}",
                "kind":"STATUS_CHANGE",
            })
        previous[key]=row["status"]
    events.sort(key=lambda x:int(x["time"] or 0),reverse=True)
    return events[:limit]


@app.get("/api/history")
def history(hours:int=24, scope:str=Query(default="EXTERNAL")):
    hours=max(1,min(hours,720)); since=int(time.time())-hours*3600
    scope=scope.upper()
    scope_key={"EXTERNAL":"GLOBAL","DOMESTIC":"RUSSIA"}.get(scope,scope)
    if scope_key not in {"GLOBAL","RUSSIA","USER"}:
        raise HTTPException(400,"scope must be EXTERNAL, DOMESTIC or USER")
    with db() as conn:
        rows=conn.execute("SELECT resource_id,checked_at,status,response_time_ms FROM checks WHERE checked_at>=? AND probe_scope=? ORDER BY checked_at ASC",(since,scope_key)).fetchall()
    buckets={}; size=max(60,(hours*3600)//240)
    for row in rows:
        bucket=(row["checked_at"]//size)*size; data=buckets.setdefault(bucket,{"timestamp":bucket,"total":0,"ok":0,"latency_sum":0})
        data["total"]+=1; data["ok"]+=int(is_reachable(row["status"])); data["latency_sum"]+=row["response_time_ms"]
    return [{"timestamp":v["timestamp"],"availability":round(v["ok"]/v["total"]*100) if v["total"] else 0,
      "avg_latency_ms":round(v["latency_sum"]/v["total"]) if v["total"] else 0,"checks":v["total"]} for v in buckets.values()]


@app.exception_handler(Exception)
async def unhandled_exception(_request,exc:Exception):
    return JSONResponse(status_code=500,content={"detail":"Internal server error","type":exc.__class__.__name__})


if FRONTEND_DIR.exists():
    assets=FRONTEND_DIR/"assets"
    if assets.exists(): app.mount("/assets",StaticFiles(directory=assets),name="assets")
    @app.api_route("/{full_path:path}",methods=["GET","HEAD"])
    def spa(full_path:str):
        if full_path == "api" or full_path.startswith("api/"):
            return JSONResponse(status_code=404,content={"detail":"Not Found"})
        root=FRONTEND_DIR.resolve()
        index=root/"index.html"
        if not full_path:
            return FileResponse(index)
        try:
            candidate=(root/full_path).resolve()
            candidate.relative_to(root)
        except (OSError,ValueError):
            return FileResponse(index)
        return FileResponse(candidate if candidate.exists() and candidate.is_file() else index)
