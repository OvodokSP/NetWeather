from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ProviderSubmission:
    provider: str
    external_id: str
    status: str
    raw: dict[str, Any]


class MeasurementProvider(ABC):
    name: str

    @abstractmethod
    async def submit_http(self, target: str, probes: int = 3) -> ProviderSubmission:
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
        payload = {
            "type": "http",
            "target": target,
            "locations": [{"magic": "world"}],
            "limit": max(1, min(probes, 10)),
            "measurementOptions": {"request": {"method": "GET"}},
        }
        async with httpx.AsyncClient(timeout=12, headers=headers) as client:
            response = await client.post(f"{self.base_url}/measurements", json=payload)
            response.raise_for_status()
            data = response.json()
        measurement_id = str(data.get("id") or "")
        if not measurement_id:
            raise RuntimeError("Globalping did not return a measurement id")
        return ProviderSubmission(self.name, measurement_id, str(data.get("status") or "queued"), data)
