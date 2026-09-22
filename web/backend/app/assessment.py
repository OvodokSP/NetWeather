from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .availability import is_reachable


class IncidentClassification(StrEnum):
    OK = "OK"
    SERVICE_DOWN = "SERVICE_DOWN"
    DEGRADED = "DEGRADED"
    LOCAL_NETWORK = "LOCAL_NETWORK"
    ISP_OUTAGE = "ISP_OUTAGE"
    DNS_FAILURE = "DNS_FAILURE"
    ROUTING_FAILURE = "ROUTING_FAILURE"
    REGIONAL_OUTAGE = "REGIONAL_OUTAGE"
    POSSIBLE_FILTERING = "POSSIBLE_FILTERING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class IncidentAssessment:
    classification: IncidentClassification
    confidence: str
    explanation: str


def assess_incident(
    global_status: str | None,
    user_status: str | None = None,
    *,
    global_slow: bool = False,
    user_slow: bool = False,
    external_failures: int = 0,
    ooni_signal: bool = False,
    external_classification: str | None = None,
    ioda_signal: bool = False,
) -> IncidentAssessment:
    """Return a deterministic conclusion without inventing unavailable evidence."""
    if not global_status:
        return IncidentAssessment(IncidentClassification.UNKNOWN, "none", "Нет данных глобального мониторинга")

    global_ok = is_reachable(global_status)
    user_ok = is_reachable(user_status) if user_status else None

    if ooni_signal and global_ok and user_status and not user_ok:
        return IncidentAssessment(
            IncidentClassification.POSSIBLE_FILTERING,
            "medium",
            "Глобально ресурс доступен, локальная проверка неуспешна, есть внешний сигнал OONI",
        )
    if global_ok and user_ok is False:
        kind = IncidentClassification.DNS_FAILURE if user_status == "DNS_ERROR" else IncidentClassification.LOCAL_NETWORK
        return IncidentAssessment(kind, "medium", "Глобально ресурс доступен, но из вашей сети проверка не прошла")
    if not global_ok and user_ok is True:
        return IncidentAssessment(
            IncidentClassification.ROUTING_FAILURE,
            "medium",
            "Из вашей сети ресурс доступен, но базовая VPS-проверка не прошла",
        )
    if not global_ok:
        if external_classification == "DNS_FAILURE":
            return IncidentAssessment(IncidentClassification.DNS_FAILURE, "high", "DNS-сбой подтверждён внешними точками Globalping")
        if external_classification == "SERVICE_DOWN":
            return IncidentAssessment(IncidentClassification.SERVICE_DOWN, "high", "Недоступность подтверждена несколькими внешними точками Globalping")
        if external_classification == "REGIONAL_OUTAGE" or ioda_signal:
            return IncidentAssessment(
                IncidentClassification.REGIONAL_OUTAGE,
                "high" if external_classification == "REGIONAL_OUTAGE" and ioda_signal else "medium",
                "Есть независимые признаки регионального сбоя",
            )
        if global_status == "DNS_ERROR" and (not user_status or user_status == "DNS_ERROR"):
            return IncidentAssessment(IncidentClassification.DNS_FAILURE, "medium", "DNS-разрешение не удалось")
        return IncidentAssessment(
            IncidentClassification.SERVICE_DOWN,
            "low" if user_status is None else "medium",
            "Базовая VPS-проверка неуспешна; запрошено внешнее подтверждение",
        )
    if global_slow or user_slow:
        return IncidentAssessment(IncidentClassification.DEGRADED, "medium", "Ресурс доступен, но отклик выше порога")
    return IncidentAssessment(
        IncidentClassification.OK,
        "high" if user_ok is True else "global",
        "Глобальная доступность подтверждена" if user_ok is None else "Глобальная и локальная проверки успешны",
    )
