from __future__ import annotations

import asyncio
import subprocess
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import (
    ALERT_WEBHOOK_URL, ALLOW_PRIVATE_TARGETS, API_TOKEN, APP_VERSION, DEFAULT_INTERVAL,
    FRONTEND_DIR, KNOWN_GROUPS, ResourceCreate, ResourcePatch, SCHEDULER_ENABLED, STARTED_AT,
    normalize_group, normalize_target,
)
from .database import db, get_incidents, init_db, latest_resources, seed_defaults, summary
from .incidents import write_check
from .monitor import perform_check, traceroute_to_resource


def require_token(authorization: str | None = Header(default=None)) -> None:
    if not API_TOKEN:
        raise HTTPException(503, "NETWEATHER_API_TOKEN is not configured")
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(401, "Invalid API token")


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
      "default_interval_seconds":DEFAULT_INTERVAL,"scheduler_enabled":SCHEDULER_ENABLED}


@app.get("/api/auth/verify", dependencies=[Depends(require_token)])
def verify_token():
    return {"ok":True}


@app.get("/api/dashboard")
def dashboard():
    return {"summary":summary(),"resources":latest_resources(),"incidents":get_incidents(True,20)}


@app.get("/api/groups")
def groups():
    values=sorted(set(KNOWN_GROUPS)|{r["group_name"] for r in latest_resources()})
    return [{"id":v,"title":KNOWN_GROUPS.get(v,v)} for v in values]


@app.get("/api/resources")
def list_resources():
    return latest_resources()


@app.get("/api/resources/{resource_id}")
def resource_details(resource_id:int):
    rows=[r for r in latest_resources() if r["id"]==resource_id]
    if not rows: raise HTTPException(404,"Resource not found")
    with db() as conn:
        checks=conn.execute("SELECT * FROM checks WHERE resource_id=? ORDER BY checked_at DESC,id DESC LIMIT 30",(resource_id,)).fetchall()
    return {"resource":rows[0],"checks":[dict(r) for r in checks],"incidents":[i for i in get_incidents(False,200) if i["resource_id"]==resource_id][:20]}


@app.post("/api/resources", dependencies=[Depends(require_token)])
def create_resource(payload:ResourceCreate):
    target=normalize_target(payload.target)
    if payload.expected_status_min>payload.expected_status_max: raise HTTPException(400,"Expected status min must be <= max")
    now=int(time.time())
    with db() as conn:
        cur=conn.execute("""INSERT INTO resources(name,target,group_name,interval_seconds,enabled,created_at,updated_at,last_checked_at,
          expected_status_min,expected_status_max,slow_threshold_ms,failure_threshold,alerts_enabled,last_success_at,last_failure_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(payload.name,target,normalize_group(payload.group_name),payload.interval_seconds,int(payload.enabled),now,now,0,
          payload.expected_status_min,payload.expected_status_max,payload.slow_threshold_ms,payload.failure_threshold,int(payload.alerts_enabled),0,0))
    return {"id":cur.lastrowid}


@app.patch("/api/resources/{resource_id}", dependencies=[Depends(require_token)])
def patch_resource(resource_id:int,payload:ResourcePatch):
    values=payload.model_dump(exclude_none=True)
    if "target" in values: values["target"]=normalize_target(values["target"])
    if "group_name" in values: values["group_name"]=normalize_group(values["group_name"])
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


@app.post("/api/resources/{resource_id}/check", dependencies=[Depends(require_token)])
async def manual_check(resource_id:int): return await check_resource(resource_id)


@app.post("/api/resources/{resource_id}/trace", dependencies=[Depends(require_token)])
async def trace_resource(resource_id:int): return await traceroute_to_resource(resource_id)


@app.post("/api/check-all", dependencies=[Depends(require_token)])
async def check_all():
    with db() as conn: rows=conn.execute("SELECT * FROM resources WHERE enabled=1").fetchall()
    results=await asyncio.gather(*(perform_check(row) for row in rows))
    for row,result in zip(rows,results): write_check(row["id"],result)
    return {"checked":len(rows),"ok":sum(1 for r in results if r["status"]=="OK"),"failed":sum(1 for r in results if r["status"]!="OK")}


@app.get("/api/incidents")
def incidents(active:bool=Query(default=False),limit:int=Query(default=100,ge=1,le=500)):
    return get_incidents(active,limit)


@app.post("/api/incidents/{incident_id}/ack", dependencies=[Depends(require_token)])
def acknowledge_incident(incident_id:int):
    with db() as conn: cur=conn.execute("UPDATE incidents SET acknowledged_at=? WHERE id=?",(int(time.time()),incident_id))
    if cur.rowcount==0: raise HTTPException(404,"Incident not found")
    return {"ok":True}


@app.get("/api/history")
def history(hours:int=24):
    hours=max(1,min(hours,720)); since=int(time.time())-hours*3600
    with db() as conn:
        rows=conn.execute("SELECT resource_id,checked_at,status,response_time_ms FROM checks WHERE checked_at>=? ORDER BY checked_at ASC",(since,)).fetchall()
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
