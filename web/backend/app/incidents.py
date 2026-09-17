from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .config import ALERT_WEBHOOK_URL
from .database import db


def _open(conn,resource_id:int,kind:str,severity:str,message:str,now:int):
    if conn.execute("SELECT id FROM incidents WHERE resource_id=? AND kind=? AND closed_at IS NULL LIMIT 1",(resource_id,kind)).fetchone(): return None
    return int(conn.execute("INSERT INTO incidents(resource_id,kind,severity,opened_at,message) VALUES(?,?,?,?,?)",(resource_id,kind,severity,now,message)).lastrowid)


def _close(conn,resource_id:int,kind:str,now:int):
    rows=conn.execute("SELECT id FROM incidents WHERE resource_id=? AND kind=? AND closed_at IS NULL",(resource_id,kind)).fetchall()
    if rows: conn.execute("UPDATE incidents SET closed_at=? WHERE resource_id=? AND kind=? AND closed_at IS NULL",(now,resource_id,kind))
    return [int(r["id"]) for r in rows]


def _post(payload):
    if not ALERT_WEBHOOK_URL: return
    try: httpx.post(ALERT_WEBHOOK_URL,json=payload,timeout=4)
    except Exception: pass


def _notify(payload):
    if not ALERT_WEBHOOK_URL: return
    try: asyncio.get_running_loop().run_in_executor(None,_post,payload)
    except RuntimeError: pass


def write_check(resource_id:int,payload:dict[str,Any])->None:
    now=int(time.time()); notices=[]
    with db() as conn:
        r=conn.execute("SELECT * FROM resources WHERE id=?",(resource_id,)).fetchone()
        if not r: return
        conn.execute("""INSERT INTO checks(resource_id,checked_at,status,response_time_ms,dns_ms,tcp_ms,tls_ms,http_ms,http_status,resolved_ip,message,tls_days_left,final_url,location)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(resource_id,now,payload["status"],payload["response_time_ms"],payload["dns_ms"],payload["tcp_ms"],payload["tls_ms"],payload["http_ms"],payload["http_status"],payload["resolved_ip"],payload["message"],payload.get("tls_days_left"),payload.get("final_url"),payload.get("location")))
        if payload["status"]=="OK": conn.execute("UPDATE resources SET last_checked_at=?,last_success_at=?,updated_at=? WHERE id=?",(now,now,now,resource_id))
        else: conn.execute("UPDATE resources SET last_checked_at=?,last_failure_at=?,updated_at=? WHERE id=?",(now,now,now,resource_id))
        conn.execute("DELETE FROM checks WHERE checked_at<?",(now-2592000,))
        if not r["alerts_enabled"]: return
        threshold=max(1,int(r["failure_threshold"] or 2))
        recent=conn.execute("SELECT status FROM checks WHERE resource_id=? ORDER BY checked_at DESC,id DESC LIMIT ?",(resource_id,threshold)).fetchall()
        failing=len(recent)>=threshold and all(x["status"]!="OK" for x in recent)
        if failing:
            iid=_open(conn,resource_id,"DOWN","critical",f"{r['name']}: {payload['status']} — {payload['message']}",now)
            if iid: notices.append({"event":"incident_opened","incident_id":iid,"resource":r["name"],"kind":"DOWN","severity":"critical","message":payload["message"],"time":now})
        elif payload["status"]=="OK":
            for iid in _close(conn,resource_id,"DOWN",now): notices.append({"event":"incident_closed","incident_id":iid,"resource":r["name"],"kind":"DOWN","severity":"info","message":"Доступ восстановлен","time":now})
        slow=payload["status"]=="OK" and payload["response_time_ms"]>=int(r["slow_threshold_ms"] or 1500)
        if slow:
            iid=_open(conn,resource_id,"SLOW","warning",f"{r['name']}: отклик {payload['response_time_ms']} мс выше порога {r['slow_threshold_ms']} мс",now)
            if iid: notices.append({"event":"incident_opened","incident_id":iid,"resource":r["name"],"kind":"SLOW","severity":"warning","message":"Высокая задержка","time":now})
        elif payload["status"]=="OK": _close(conn,resource_id,"SLOW",now)
        days=payload.get("tls_days_left")
        if days is not None and days<=14:
            iid=_open(conn,resource_id,"TLS_EXPIRY","warning",f"{r['name']}: TLS-сертификат истекает через {days} дн.",now)
            if iid: notices.append({"event":"incident_opened","incident_id":iid,"resource":r["name"],"kind":"TLS_EXPIRY","severity":"warning","message":f"TLS: {days} дн.","time":now})
        elif days is not None and days>14: _close(conn,resource_id,"TLS_EXPIRY",now)
    for notice in notices: _notify(notice)
