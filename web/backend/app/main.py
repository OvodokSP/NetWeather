from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import subprocess
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import (
    AGENT_TOKEN, ALERT_WEBHOOK_URL, ALLOW_PRIVATE_TARGETS, API_TOKEN, APP_VERSION, AUTH_REQUIRED, DEFAULT_INTERVAL,
    FRONTEND_DIR, KNOWN_GROUPS, ResourceCreate, ResourcePatch, AgentResult, CatalogAddRequest, GroupCreate, GroupPatch,
    OwnerLogin, SCHEDULER_ENABLED, SESSION_MAX_AGE, STARTED_AT, UI_PASSWORD,
    normalize_group, normalize_target,
)
from .database import (
    db, dual_summary, get_incidents, init_db, latest_resources, probe_statuses,
    register_probe, resource_groups, resource_matrix, seed_defaults, summary,
)
from .incidents import write_check
from .monitor import discover_target_metadata, perform_check, traceroute_to_resource
from .resource_catalog import CATALOG_BY_KEY, catalog_match, catalog_payload


SESSION_COOKIE = "netweather_owner"


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


def require_agent(x_netweather_agent: str | None = Header(default=None)) -> None:
    if not AGENT_TOKEN:
        raise HTTPException(503, "NETWEATHER_AGENT_TOKEN is not configured")
    if x_netweather_agent != AGENT_TOKEN:
        raise HTTPException(401, "Invalid probe token")


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
        write_check(row["id"], payload)
    except Exception as exc:
        write_check(row["id"], {
            "status":"UNKNOWN_ERROR","response_time_ms":0,"dns_ms":None,"tcp_ms":None,"tls_ms":None,
            "http_ms":None,"http_status":None,"resolved_ip":None,"tls_days_left":None,"final_url":row["target"],
            "location":None,"message":str(exc),
        })


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
    init_db()
    seed_defaults()
    task = asyncio.create_task(scheduler()) if SCHEDULER_ENABLED else None
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="NetWeather API", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST","PATCH","DELETE","HEAD"], allow_headers=["*"])


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
      "default_interval_seconds":DEFAULT_INTERVAL,"scheduler_enabled":SCHEDULER_ENABLED,
      "auth_required":AUTH_REQUIRED}


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


@app.get("/api/target-meta")
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
      last_success_at,last_failure_at,catalog_key
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (item.name,normalize_target(item.target),item.group_key,interval_seconds,int(enabled),now,now,0,
     expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,int(alerts_enabled),0,0,item.key))
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


@app.post("/api/resource-catalog/add", dependencies=[Depends(require_token)])
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
    return {"resource":rows[0],"checks":[dict(r) for r in checks],"incidents":[i for i in get_incidents(False,200) if i["resource_id"]==resource_id][:20]}


@app.post("/api/resources", dependencies=[Depends(require_token)])
def create_resource(payload:ResourceCreate):
    target=normalize_target(payload.target)
    if payload.expected_status_min>payload.expected_status_max:
        raise HTTPException(400,"Expected status min must be <= max")
    now=int(time.time())
    match=catalog_match(target)
    with db() as conn:
        if match:
            resource_id,created=_insert_catalog_resource(
                conn,match,now,
                interval_seconds=payload.interval_seconds,
                expected_status_min=payload.expected_status_min,
                expected_status_max=payload.expected_status_max,
                slow_threshold_ms=payload.slow_threshold_ms,
                failure_threshold=payload.failure_threshold,
                alerts_enabled=payload.alerts_enabled,
                enabled=payload.enabled,
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
        _ensure_resource_group(conn,group_name,now)
        cur=conn.execute("""INSERT INTO resources(
          name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at,
          expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,alerts_enabled,
          last_success_at,last_failure_at,catalog_key
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
        (payload.name,target,group_name,payload.interval_seconds,int(payload.enabled),now,now,0,
         payload.expected_status_min,payload.expected_status_max,payload.slow_threshold_ms,payload.failure_threshold,
         int(payload.alerts_enabled),0,0))
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
        else:
            values["catalog_key"]=None
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


def schedule_domestic_checks(resource_ids:list[int]) -> int:
    online = [p for p in probe_statuses() if p["scope"] == "DOMESTIC" and p["online"]]
    if not online or not resource_ids:
        return 0
    now = int(time.time())
    count = 0
    with db() as conn:
        for probe in online:
            for resource_id in resource_ids:
                exists = conn.execute("""SELECT 1 FROM probe_tasks
                  WHERE probe_key=? AND resource_id=? AND task_type='CHECK' AND status='PENDING' LIMIT 1""",
                  (probe["probe_key"], resource_id)).fetchone()
                if exists:
                    continue
                conn.execute("""INSERT INTO probe_tasks(probe_key,resource_id,task_type,status,created_at)
                  VALUES(?,?, 'CHECK', 'PENDING', ?)""", (probe["probe_key"], resource_id, now))
                count += 1
    return count


@app.post("/api/resources/{resource_id}/check", dependencies=[Depends(require_token)])
async def manual_check(resource_id:int):
    payload = await check_resource(resource_id)
    payload["scheduled_domestic"] = schedule_domestic_checks([resource_id])
    return payload


@app.post("/api/resources/{resource_id}/trace", dependencies=[Depends(require_token)])
async def trace_resource(resource_id:int): return await traceroute_to_resource(resource_id)


@app.get("/api/agent/config.tsv", dependencies=[Depends(require_agent)])
def agent_config(probe_key: str = Query(min_length=1,max_length=80), probe_name: str = Query(default="Российский probe",max_length=120)):
    register_probe(probe_key, probe_name, "DOMESTIC")
    rows = []
    with db() as conn:
        resources = conn.execute("""SELECT id,name,target,expected_status_min,expected_status_max,enabled
          FROM resources WHERE enabled=1 ORDER BY id""").fetchall()
    for r in resources:
        rows.append("\t".join([
            str(r["id"]), r["name"].replace("\t"," "), r["target"],
            str(r["expected_status_min"]), str(r["expected_status_max"])
        ]))
    return Response(content="\n".join(rows)+("\n" if rows else ""), media_type="text/tab-separated-values; charset=utf-8")


@app.post("/api/agent/result", dependencies=[Depends(require_agent)])
def agent_result(payload: AgentResult, probe_key: str = Query(min_length=1,max_length=80), probe_name: str = Query(default="Российский probe",max_length=120)):
    register_probe(probe_key, probe_name, "DOMESTIC")
    with db() as conn:
        exists = conn.execute("SELECT 1 FROM resources WHERE id=?", (payload.resource_id,)).fetchone()
    if not exists:
        raise HTTPException(404, "Resource not found")
    data = payload.model_dump()
    data.update({"tls_days_left":None,"final_url":None,"location":None})
    write_check(payload.resource_id, data, probe_key=probe_key, probe_scope="DOMESTIC")
    return {"ok":True}


@app.get("/api/agent/tasks.tsv", dependencies=[Depends(require_agent)])
def agent_tasks(probe_key: str = Query(min_length=1,max_length=80), probe_name: str = Query(default="Российский probe",max_length=120)):
    register_probe(probe_key, probe_name, "DOMESTIC")
    with db() as conn:
        rows = conn.execute("""SELECT t.id,t.resource_id,t.task_type,r.target,r.expected_status_min,r.expected_status_max FROM probe_tasks t
          JOIN resources r ON r.id=t.resource_id
          WHERE t.probe_key=? AND t.status='PENDING'
          ORDER BY t.created_at LIMIT 10""", (probe_key,)).fetchall()
    return Response(
        content="".join(f"{r['id']}\t{r['resource_id']}\t{r['task_type']}\t{r['target']}\t{r['expected_status_min']}\t{r['expected_status_max']}\n" for r in rows),
        media_type="text/tab-separated-values; charset=utf-8",
    )


@app.post("/api/agent/tasks/{task_id}/complete", dependencies=[Depends(require_agent)])
async def agent_task_complete(task_id:int, request:Request, probe_key:str=Query(min_length=1,max_length=80)):
    text_body = (await request.body()).decode("utf-8", errors="replace")[:20000]
    now = int(time.time())
    with db() as conn:
        cur = conn.execute("""UPDATE probe_tasks SET status='DONE',completed_at=?,result_text=?
          WHERE id=? AND probe_key=?""", (now,text_body,task_id,probe_key))
    if cur.rowcount == 0:
        raise HTTPException(404, "Task not found")
    return {"ok":True}


@app.post("/api/resources/{resource_id}/trace-domestic", dependencies=[Depends(require_token)])
def trace_domestic(resource_id:int, probe_key:str=Query(default="RU_HOME",min_length=1,max_length=80)):
    with db() as conn:
        if not conn.execute("SELECT 1 FROM resources WHERE id=?", (resource_id,)).fetchone():
            raise HTTPException(404, "Resource not found")
        now = int(time.time())
        cur = conn.execute("""INSERT INTO probe_tasks(probe_key,resource_id,task_type,status,created_at)
          VALUES(?,?, 'TRACE', 'PENDING', ?)""", (probe_key,resource_id,now))
    return {"task_id":cur.lastrowid,"status":"PENDING"}


@app.get("/api/trace-tasks/{task_id}")
def trace_task(task_id:int):
    with db() as conn:
        row = conn.execute("""SELECT t.*,r.name resource_name,r.target FROM probe_tasks t
          JOIN resources r ON r.id=t.resource_id WHERE t.id=?""", (task_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Trace task not found")
    return dict(row)


@app.post("/api/check-all", dependencies=[Depends(require_token)])
async def check_all():
    with db() as conn: rows=conn.execute("SELECT * FROM resources WHERE enabled=1").fetchall()
    results=await asyncio.gather(*(perform_check(row) for row in rows))
    for row,result in zip(rows,results): write_check(row["id"],result)
    scheduled_domestic = schedule_domestic_checks([int(row["id"]) for row in rows])
    return {"checked":len(rows),"ok":sum(1 for r in results if r["status"]=="OK"),"failed":sum(1 for r in results if r["status"]!="OK"),"scheduled_domestic":scheduled_domestic}


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
    if scope not in {"EXTERNAL","DOMESTIC"}:
        raise HTTPException(400,"scope must be EXTERNAL or DOMESTIC")
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
          (since-availability_window,scope)).fetchall()
        stats24=conn.execute("""SELECT resource_id,
          COUNT(*) total,
          SUM(CASE WHEN status='OK' THEN 1 ELSE 0 END) ok,
          AVG(response_time_ms) avg_latency,
          MAX(checked_at) last_checked
          FROM checks WHERE checked_at>=? AND probe_scope=? GROUP BY resource_id""",
          (now-86400,scope)).fetchall()
    stats={int(r["resource_id"]):dict(r) for r in stats24}
    by_resource={}
    for row in rows:
        rid=int(row["resource_id"])
        b=(int(row["checked_at"])//bucket)*bucket
        target=by_resource.setdefault(rid,{})
        point=target.setdefault(b,{"timestamp":b,"total":0,"ok":0,"latency_sum":0,"latency_count":0})
        point["total"]+=1
        point["ok"]+=int(row["status"]=="OK")
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
        if old is not None and old!=row["status"]:
            events.append({
                "type":"status_change",
                "time":row["checked_at"],
                "resource_id":row["resource_id"],
                "resource_name":row["resource_name"],
                "severity":"info" if row["status"]=="OK" else "warning",
                "title":("Восстановление " if row["status"]=="OK" else "Изменение состояния ")+row["resource_name"],
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
    if scope not in {"EXTERNAL","DOMESTIC"}:
        raise HTTPException(400,"scope must be EXTERNAL or DOMESTIC")
    with db() as conn:
        rows=conn.execute("SELECT resource_id,checked_at,status,response_time_ms FROM checks WHERE checked_at>=? AND probe_scope=? ORDER BY checked_at ASC",(since,scope)).fetchall()
    buckets={}; size=max(60,(hours*3600)//240)
    for row in rows:
        bucket=(row["checked_at"]//size)*size; data=buckets.setdefault(bucket,{"timestamp":bucket,"total":0,"ok":0,"latency_sum":0})
        data["total"]+=1; data["ok"]+=int(row["status"]=="OK"); data["latency_sum"]+=row["response_time_ms"]
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
        candidate=FRONTEND_DIR/full_path
        return FileResponse(candidate if full_path and candidate.exists() and candidate.is_file() else FRONTEND_DIR/"index.html")
