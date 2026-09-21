from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


@dataclass(frozen=True)
class IntelligenceEvidence:
    provider: str
    status: str
    classification: str
    confidence: str
    summary: dict[str, Any]
    raw: dict[str, Any]


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
