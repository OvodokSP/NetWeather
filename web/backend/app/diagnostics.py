from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import IntEnum

from .providers import MeasurementProvider, ProviderSubmission


class DiagnosticPriority(IntEnum):
    MANUAL = 0
    NEW_DOWN = 1
    DEGRADED = 2
    RECHECK = 3
    BACKGROUND = 4


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    reason: str
    used: int
    limit: int
    reserve: int


class QuotaManager:
    """Hourly provider budget with a protected failure/manual reserve."""

    def __init__(self, hourly_limit: int = 250, reserve_percent: int = 30) -> None:
        self.hourly_limit = max(1, hourly_limit)
        self.reserve_percent = max(0, min(reserve_percent, 90))
        self._uses: deque[tuple[float, int, DiagnosticPriority]] = deque()

    def _prune(self, now: float) -> None:
        while self._uses and now - self._uses[0][0] >= 3600:
            self._uses.popleft()

    def status(self, now: float | None = None) -> dict[str, int]:
        now = time.time() if now is None else now
        self._prune(now)
        used = sum(cost for _, cost, _ in self._uses)
        reserve = round(self.hourly_limit * self.reserve_percent / 100)
        return {"used": used, "limit": self.hourly_limit, "reserve": reserve, "remaining": max(0, self.hourly_limit - used)}

    def consume(self, priority: DiagnosticPriority, cost: int, now: float | None = None) -> QuotaDecision:
        now = time.time() if now is None else now
        cost = max(1, cost)
        state = self.status(now)
        ceiling = state["limit"] if priority <= DiagnosticPriority.NEW_DOWN else state["limit"] - state["reserve"]
        allowed = state["used"] + cost <= ceiling
        if allowed:
            self._uses.append((now, cost, priority))
        reason = "allowed" if allowed else ("reserve_protected" if state["used"] + cost <= state["limit"] else "quota_exhausted")
        return QuotaDecision(allowed, reason, state["used"], state["limit"], state["reserve"])


class DiagnosticCoordinator:
    def __init__(self, provider: MeasurementProvider, quota: QuotaManager, cooldown_seconds: int = 900) -> None:
        self.provider = provider
        self.quota = quota
        self.cooldown_seconds = max(30, cooldown_seconds)
        self._last: dict[tuple[int, str], float] = {}

    async def request(self, resource_id: int, target: str, priority: DiagnosticPriority, probes: int = 3) -> ProviderSubmission:
        key = (resource_id, self.provider.name)
        now = time.time()
        if priority != DiagnosticPriority.MANUAL and now - self._last.get(key, 0) < self.cooldown_seconds:
            raise RuntimeError("diagnostic cooldown is active")
        decision = self.quota.consume(priority, probes, now)
        if not decision.allowed:
            raise RuntimeError(decision.reason)
        result = await self.provider.submit_http(target, probes)
        self._last[key] = now
        return result
