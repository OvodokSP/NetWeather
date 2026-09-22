from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class ProviderSubmission:
    provider: str
    external_id: str
    status: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    external_id: str
    status: str
    classification: str | None
    confidence: str | None
    summary: dict[str, Any]
    raw: dict[str, Any]


class MeasurementProvider(ABC):
    name: str

    @abstractmethod
    async def submit_http(self, target: str, probes: int = 3) -> ProviderSubmission:
        raise NotImplementedError

    @abstractmethod
    async def get_result(self, external_id: str) -> ProviderResult:
        raise NotImplementedError


class GlobalpingProvider(MeasurementProvider):
    name = "globalping"

    def __init__(self, token: str = "", base_url: str = "https://api.globalping.io/v1") -> None:
        self.token = token.strip()
        self.base_url = base_url.rstrip("/")

    async def submit_http(self, target: str, probes: int = 3) -> ProviderSubmission:
        headers = {"User-Agent": "NetWeather/0.4", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        parsed = urlparse(target if "://" in target else f"https://{target}")
        hostname = parsed.hostname or target
        protocol = "HTTP" if parsed.scheme.lower() == "http" else "HTTPS"
        request_options: dict[str, Any] = {"method": "GET"}
        if parsed.path and parsed.path != "/":
            request_options["path"] = parsed.path
        if parsed.query:
            request_options["query"] = parsed.query
        options: dict[str, Any] = {"protocol": protocol, "request": request_options}
        if parsed.port:
            options["port"] = parsed.port
        payload = {
            "type": "http",
            # Globalping's MeasurementTarget is a hostname/IP. Protocol, port
            # and URL path are represented in measurementOptions instead of
            # passing a browser URL as the target.
            "target": hostname,
            "locations": [{"magic": "world"}],
            "limit": max(1, min(probes, 10)),
            "measurementOptions": options,
        }
        async with httpx.AsyncClient(timeout=12, headers=headers) as client:
            response = await client.post(f"{self.base_url}/measurements", json=payload)
            response.raise_for_status()
            data = response.json()
        measurement_id = str(data.get("id") or "")
        if not measurement_id:
            raise RuntimeError("Globalping did not return a measurement id")
        return ProviderSubmission(self.name, measurement_id, str(data.get("status") or "queued"), data)

    async def get_result(self, external_id: str) -> ProviderResult:
        headers = {"User-Agent": "NetWeather/0.4", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        async with httpx.AsyncClient(timeout=12, headers=headers) as client:
            response = await client.get(f"{self.base_url}/measurements/{external_id}")
            response.raise_for_status()
            data = response.json()
        status = str(data.get("status") or "in-progress")
        if status not in {"finished", "failed", "error"}:
            return ProviderResult(self.name, external_id, status, None, None, {
                "total": len(data.get("results") or []), "complete": False,
            }, data)
        if status in {"failed", "error"}:
            return ProviderResult(self.name, external_id, status, "UNKNOWN", "none", {
                "total": len(data.get("results") or []), "complete": True,
                "provider_status": status,
            }, data)
        summary = classify_globalping_http(data)
        return ProviderResult(
            self.name, external_id, "finished", summary["classification"],
            summary["confidence"], summary, data,
        )


def classify_globalping_http(data: dict[str, Any]) -> dict[str, Any]:
    """Aggregate documented per-probe HTTP results into conservative evidence."""
    results = data.get("results") if isinstance(data.get("results"), list) else []
    total = len(results)
    reachable = 0
    service_errors = 0
    failed = 0
    resolver_failures = 0
    target_failures = 0
    internal_failures = 0
    latencies: list[int] = []
    countries: set[str] = set()
    failing_countries: set[str] = set()
    for entry in results:
        if not isinstance(entry, dict):
            continue
        probe = entry.get("probe") if isinstance(entry.get("probe"), dict) else {}
        country = str(probe.get("country") or "").upper()
        if country:
            countries.add(country)
        result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
        result_status = str(result.get("status") or "")
        status_code = result.get("statusCode")
        if result_status == "finished" and isinstance(status_code, int):
            reachable += 1
            if status_code >= 500:
                service_errors += 1
            timings = result.get("timings") if isinstance(result.get("timings"), dict) else {}
            if isinstance(timings.get("total"), (int, float)):
                latencies.append(round(timings["total"]))
            continue
        failed += 1
        if country:
            failing_countries.add(country)
        source = str(result.get("failureSource") or "")
        if source == "resolver":
            resolver_failures += 1
        elif source == "target":
            target_failures += 1
        else:
            internal_failures += 1
    valid = reachable + failed
    independent_failures = max(0, failed - internal_failures)
    if valid == 0:
        classification, confidence = "UNKNOWN", "none"
    elif resolver_failures >= 2 and resolver_failures * 2 >= valid:
        classification, confidence = "DNS_FAILURE", "high" if valid >= 3 else "medium"
    elif reachable == 0 and target_failures >= 2 and len(failing_countries) >= 2:
        classification, confidence = "SERVICE_DOWN", "high" if valid >= 3 else "medium"
    elif service_errors >= 2 and service_errors * 2 >= valid:
        classification, confidence = "SERVICE_DOWN", "high" if valid >= 3 else "medium"
    elif (reachable >= 2 and independent_failures >= 2 and len(failing_countries) == 1
          and len(countries) >= 2 and valid >= 4):
        classification, confidence = "REGIONAL_OUTAGE", "medium"
    elif reachable > 0 and failed == 0:
        classification, confidence = "OK", "high" if reachable >= 3 else "medium"
    else:
        classification, confidence = "UNKNOWN", "low"
    return {
        "complete": True,
        "classification": classification,
        "confidence": confidence,
        "total": total,
        "valid": valid,
        "reachable": reachable,
        "failed": failed,
        "resolver_failures": resolver_failures,
        "target_failures": target_failures,
        "internal_failures": internal_failures,
        "service_errors": service_errors,
        "countries": sorted(countries),
        "failing_countries": sorted(failing_countries),
        "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None,
    }
