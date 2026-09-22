from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class IntelligenceEvidence:
    provider: str
    status: str
    classification: str
    confidence: str
    summary: dict[str, Any]
    raw: dict[str, Any]


class StatusProvider(ABC):
    """Read-only interface for public, official service status pages."""

    name = "statuspage"

    @abstractmethod
    async def fetch(self, target: str) -> IntelligenceEvidence | None:
        raise NotImplementedError


class StatuspageProvider(StatusProvider):
    """Statuspage.io public summary feeds for explicitly supported services.

    The fixed allowlist avoids turning an incident refresh into a user-controlled
    outbound request. Additions to this map must point to the service's official page.
    """

    PAGES = {
        "github.com": ("GitHub", "https://www.githubstatus.com"),
        "cloudflare.com": ("Cloudflare", "https://www.cloudflarestatus.com"),
        "1.1.1.1": ("Cloudflare", "https://www.cloudflarestatus.com"),
    }

    async def fetch(self, target: str) -> IntelligenceEvidence | None:
        host = (urlparse(target).hostname or "").lower().rstrip(".").removeprefix("www.")
        page = self.PAGES.get(host)
        if not page:
            return None
        name, base_url = page
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "NetWeather/0.4"}) as client:
            response = await client.get(f"{base_url}/api/v2/summary.json")
            response.raise_for_status()
            data = response.json()
        status = data.get("status") if isinstance(data, dict) else None
        indicator = str((status or {}).get("indicator") or "unknown").lower()
        description = str((status or {}).get("description") or "")[:240]
        components = data.get("components") if isinstance(data, dict) else []
        degraded = [
            str(item.get("name") or "")[:120]
            for item in components if isinstance(item, dict)
            and str(item.get("status") or "").lower() not in {"operational", ""}
        ]
        if indicator == "none" and not degraded:
            classification, evidence_status = "OPERATIONAL", "CLEAR"
        elif indicator in {"minor", "major", "critical", "maintenance"} or degraded:
            classification, evidence_status = "PROVIDER_INCIDENT", "SIGNAL"
        else:
            classification, evidence_status = "UNKNOWN", "NO_DATA"
        incidents = data.get("incidents") if isinstance(data, dict) else []
        maintenances = data.get("scheduled_maintenances") if isinstance(data, dict) else []
        summary = {
            "service": name,
            "status_page": base_url,
            "indicator": indicator,
            "description": description,
            "degraded_components": degraded[:20],
            "active_incidents": len(incidents) if isinstance(incidents, list) else 0,
            "scheduled_maintenances": len(maintenances) if isinstance(maintenances, list) else 0,
            "updated_at": str((data.get("page") or {}).get("updated_at") or "")[:40],
        }
        return IntelligenceEvidence(self.name, evidence_status, classification, "medium", summary, {})


class OoniProvider:
    """Read-only OONI aggregation adapter for recent Web Connectivity evidence."""

    def __init__(self, base_url: str, probe_country: str = "RU") -> None:
        self.base_url = base_url.rstrip("/")
        self.probe_country = probe_country.upper()

    async def fetch(self, domain: str, hours: int = 24) -> IntelligenceEvidence:
        # OONI's aggregation API accepts calendar dates, not sub-day timestamps.
        today = datetime.now(timezone.utc).date()
        since = today - timedelta(days=2)
        until = today + timedelta(days=1)
        params = {
            "domain": domain,
            "probe_cc": self.probe_country,
            "test_name": "web_connectivity",
            "since": since.isoformat(),
            "until": until.isoformat(),
        }
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "NetWeather/0.4"}) as client:
            response = await client.get(f"{self.base_url}/aggregation", params=params)
            response.raise_for_status()
            data = response.json()
        result = data.get("result") or {}
        if isinstance(result, list):
            values = result
        elif isinstance(result, dict):
            values = [result]
        else:
            values = []
        counters = {key: sum(int(item.get(key) or 0) for item in values if isinstance(item, dict)) for key in (
            "anomaly_count", "confirmed_count", "failure_count", "ok_count", "measurement_count",
        )}
        measured = counters["measurement_count"]
        suspicious = counters["anomaly_count"] + counters["confirmed_count"]
        if measured == 0:
            classification, confidence, status = "UNKNOWN", "none", "NO_DATA"
        elif counters["confirmed_count"] >= 2:
            classification, confidence, status = "POSSIBLE_FILTERING", "high", "SIGNAL"
        elif suspicious >= 3 and suspicious / measured >= 0.35:
            classification, confidence, status = "POSSIBLE_FILTERING", "medium", "SIGNAL"
        else:
            classification, confidence, status = "NO_FILTERING_SIGNAL", "medium", "CLEAR"
        return IntelligenceEvidence("ooni", status, classification, confidence, {
            **counters, "domain": domain, "probe_country": self.probe_country,
            "window_days": 3,
        }, data)


class IodaProvider:
    """Country-level IODA outage-alert adapter used as contextual evidence only."""

    def __init__(self, base_url: str, country: str = "RU") -> None:
        self.base_url = base_url.rstrip("/")
        self.country = country.upper()

    async def fetch(self, hours: int = 24) -> IntelligenceEvidence:
        until = int(datetime.now(timezone.utc).timestamp())
        since = until - max(6, hours) * 3600
        params = {"from": since, "until": until, "entityType": "country", "entityCode": self.country}
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "NetWeather/0.4"}) as client:
            response = await client.get(f"{self.base_url}/outages/alerts", params=params)
            response.raise_for_status()
            data = response.json()
        raw_items = data.get("data", data.get("results", data.get("alerts", []))) if isinstance(data, dict) else []
        items = raw_items if isinstance(raw_items, list) else []
        relevant = []
        unscoped = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            entity = item.get("entity") if isinstance(item.get("entity"), dict) else {}
            code = str(item.get("entityCode") or item.get("entity_code") or item.get("code") or entity.get("code") or "").upper()
            if code == self.country:
                relevant.append(item)
            elif not code:
                unscoped += 1
        if relevant:
            classification, confidence, status = "REGIONAL_OUTAGE", "medium", "SIGNAL"
        elif unscoped:
            classification, confidence, status = "UNKNOWN", "none", "UNSCOPED_DATA"
        else:
            classification, confidence, status = "NO_OUTAGE_SIGNAL", "medium", "CLEAR"
        return IntelligenceEvidence("ioda", status, classification, confidence, {
            "country": self.country, "alerts": len(relevant), "window_hours": max(6, hours),
        }, {"envelope": True} if isinstance(data, dict) else {})
