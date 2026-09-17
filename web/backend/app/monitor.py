from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import ssl
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from .config import ALLOW_PRIVATE_TARGETS, APP_VERSION, REQUEST_TIMEOUT, normalize_target
from .database import db


def _forbidden(addr: ipaddress._BaseAddress) -> bool:
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast


async def resolve_host(host: str) -> tuple[str,float]:
    started=time.perf_counter(); loop=asyncio.get_running_loop()
    infos=await loop.getaddrinfo(host,None,type=socket.SOCK_STREAM)
    if not infos: raise OSError("DNS returned no addresses")
    ips=[]
    for info in infos:
        ip=info[4][0]
        if ip not in ips: ips.append(ip)
    if not ALLOW_PRIVATE_TARGETS and any(_forbidden(ipaddress.ip_address(ip)) for ip in ips):
        raise PermissionError("Private, loopback, link-local and reserved targets are blocked")
    return ips[0],(time.perf_counter()-started)*1000


async def tcp_probe(ip:str,port:int)->float:
    started=time.perf_counter(); _r,w=await asyncio.wait_for(asyncio.open_connection(ip,port),timeout=4)
    w.close(); await w.wait_closed(); return (time.perf_counter()-started)*1000


async def tls_probe(ip:str,host:str,port:int)->tuple[float,int|None]:
    started=time.perf_counter(); ctx=ssl.create_default_context()
    _r,w=await asyncio.wait_for(asyncio.open_connection(ip,port,ssl=ctx,server_hostname=host),timeout=5)
    obj=w.get_extra_info("ssl_object"); cert=obj.getpeercert() if obj else None; days=None
    if cert and cert.get("notAfter"):
        days=max(0,int((ssl.cert_time_to_seconds(cert["notAfter"])-time.time())//86400))
    w.close(); await w.wait_closed(); return (time.perf_counter()-started)*1000,days


async def perform_check(resource) -> dict[str,Any]:
    target=normalize_target(resource["target"]); parsed=urlparse(target); host=parsed.hostname or ""; port=parsed.port or (443 if parsed.scheme=="https" else 80); started=time.perf_counter()
    out={"status":"UNKNOWN_ERROR","response_time_ms":0,"dns_ms":None,"tcp_ms":None,"tls_ms":None,"http_ms":None,"http_status":None,"resolved_ip":None,"tls_days_left":None,"final_url":target,"location":None,"message":""}
    try:
        ip,dns=await resolve_host(host); out["resolved_ip"]=ip; out["dns_ms"]=round(dns)
    except PermissionError as e:
        out.update(status="BLOCKED_TARGET",message=str(e)); out["response_time_ms"]=round((time.perf_counter()-started)*1000); return out
    except Exception as e:
        out.update(status="DNS_ERROR",message=str(e)); out["response_time_ms"]=round((time.perf_counter()-started)*1000); return out
    try: out["tcp_ms"]=round(await tcp_probe(out["resolved_ip"],port))
    except Exception as e:
        out.update(status="TCP_ERROR",message=str(e)); out["response_time_ms"]=round((time.perf_counter()-started)*1000); return out
    if parsed.scheme=="https":
        try:
            tls,days=await tls_probe(out["resolved_ip"],host,port); out["tls_ms"]=round(tls); out["tls_days_left"]=days
        except Exception as e:
            out.update(status="TLS_ERROR",message=str(e)); out["response_time_ms"]=round((time.perf_counter()-started)*1000); return out
    try:
        hs=time.perf_counter()
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT,follow_redirects=False,headers={"User-Agent":f"NetWeather/{APP_VERSION}"}) as client:
            async with client.stream("GET",target) as response:
                out["http_ms"]=round((time.perf_counter()-hs)*1000); out["http_status"]=response.status_code; out["location"]=response.headers.get("location"); out["final_url"]=str(response.url)
        lo,hi=resource["expected_status_min"] or 200,resource["expected_status_max"] or 399
        if lo<=out["http_status"]<=hi: out.update(status="OK",message=f"HTTP {out['http_status']}")
        else: out.update(status="HTTP_ERROR",message=f"HTTP {out['http_status']}, expected {lo}-{hi}")
    except httpx.TimeoutException: out.update(status="TIMEOUT",message="HTTP timeout")
    except Exception as e: out.update(status="HTTP_ERROR",message=str(e))
    out["response_time_ms"]=round((time.perf_counter()-started)*1000); return out


async def traceroute_to_resource(resource_id:int)->dict[str,Any]:
    with db() as conn: resource=conn.execute("SELECT * FROM resources WHERE id=?",(resource_id,)).fetchone()
    if not resource: raise HTTPException(404,"Resource not found")
    target=normalize_target(resource["target"]); host=urlparse(target).hostname or ""; ip,dns=await resolve_host(host)
    try:
        proc=await asyncio.create_subprocess_exec("traceroute","-n","-w","1","-q","1","-m","15",ip,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
    except FileNotFoundError: raise HTTPException(503,"traceroute is not installed in monitor container")
    try: stdout,_=await asyncio.wait_for(proc.communicate(),timeout=25)
    except asyncio.TimeoutError:
        proc.kill(); await proc.communicate(); raise HTTPException(504,"Traceroute timed out")
    raw=stdout.decode("utf-8",errors="replace"); hops=[]
    for line in raw.splitlines()[1:]:
        m=re.match(r"\s*(\d+)\s+(\S+)(?:\s+([0-9.]+)\s+ms)?",line)
        if m: hops.append({"hop":int(m.group(1)),"ip":None if m.group(2)=="*" else m.group(2),"latency_ms":float(m.group(3)) if m.group(3) else None})
    return {"resource_id":resource_id,"name":resource["name"],"host":host,"resolved_ip":ip,"dns_ms":round(dns),"hops":hops,"raw":raw,"time":int(time.time())}
