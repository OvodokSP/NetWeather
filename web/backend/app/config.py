from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException
from pydantic import BaseModel, Field

APP_VERSION = "0.4.1-web"
STARTED_AT = int(time.time())
DB_PATH = Path(os.getenv("NETWEATHER_DB", "/data/netweather.db"))
API_TOKEN = os.getenv("NETWEATHER_API_TOKEN", "")
UI_PASSWORD = os.getenv("NETWEATHER_UI_PASSWORD", "").strip()
SESSION_MAX_AGE = int(os.getenv("NETWEATHER_SESSION_MAX_AGE", "2592000"))
ALLOW_OPEN_ACCESS = os.getenv("NETWEATHER_ALLOW_OPEN_ACCESS", "false").lower() in {"1","true","yes","on"}
# Production is fail-closed. Open mutation access exists only for explicit local development.
AUTH_REQUIRED = not ALLOW_OPEN_ACCESS
ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"
DEFAULT_INTERVAL = int(os.getenv("DEFAULT_INTERVAL_SECONDS", "60"))
PUBLIC_ADD_LIMIT = int(os.getenv("NETWEATHER_PUBLIC_ADD_LIMIT", "5"))
PUBLIC_ADD_WINDOW_SECONDS = int(os.getenv("NETWEATHER_PUBLIC_ADD_WINDOW_SECONDS", "3600"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))
SEED_DEFAULTS = os.getenv("NETWEATHER_SEED_DEFAULTS", "true").lower() == "true"
# Production monitoring is paused until explicitly re-enabled in a reviewed change.
SCHEDULER_ENABLED = False
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()
CLIENT_PROBE_STALE_SECONDS = int(os.getenv("NETWEATHER_CLIENT_PROBE_STALE_SECONDS", "180"))
SERVER_PROBE_STALE_SECONDS = int(os.getenv("NETWEATHER_SERVER_PROBE_STALE_SECONDS", "180"))
SERVER_PROBE_KEY = os.getenv("NETWEATHER_SERVER_PROBE_KEY", "VPS_EU").strip() or "VPS_EU"
SERVER_PROBE_NAME = os.getenv("NETWEATHER_SERVER_PROBE_NAME", "NetWeather VPS").strip() or "NetWeather VPS"
SERVER_PROBE_LAT = float(os.getenv("NETWEATHER_SERVER_PROBE_LAT", "50.11"))
SERVER_PROBE_LON = float(os.getenv("NETWEATHER_SERVER_PROBE_LON", "8.68"))
# Globalping's public API is available without a token; keep the provider on by
# default so a production deployment cannot silently degrade to a stub. A token
# may still be supplied to receive the higher authenticated quota.
GLOBALPING_ENABLED = os.getenv("NETWEATHER_GLOBALPING_ENABLED", "true").lower() in {"1","true","yes","on"}
GLOBALPING_TOKEN = os.getenv("NETWEATHER_GLOBALPING_TOKEN", "").strip()
GLOBALPING_BASE_URL = os.getenv("NETWEATHER_GLOBALPING_BASE_URL", "https://api.globalping.io/v1").rstrip("/")
GLOBALPING_HOURLY_LIMIT = int(os.getenv("NETWEATHER_GLOBALPING_HOURLY_LIMIT", "250"))
RUSSIA_CHECK_INTERVAL_SECONDS = int(os.getenv("NETWEATHER_RUSSIA_CHECK_INTERVAL_SECONDS", "900"))
RUSSIA_PROBE_COUNT = int(os.getenv("NETWEATHER_RUSSIA_PROBE_COUNT", "3"))
RUSSIA_PROBE_KEY = os.getenv("NETWEATHER_RUSSIA_PROBE_KEY", "GLOBALPING_RU").strip() or "GLOBALPING_RU"
RUSSIA_PROBE_NAME = os.getenv("NETWEATHER_RUSSIA_PROBE_NAME", "Публичные точки РФ (Globalping)").strip() or "Публичные точки РФ (Globalping)"
RUSSIA_PROBE_STALE_SECONDS = int(os.getenv("NETWEATHER_RUSSIA_PROBE_STALE_SECONDS", "1800"))
RUSSIA_PROBE_LAT = float(os.getenv("NETWEATHER_RUSSIA_PROBE_LAT", "55.75"))
RUSSIA_PROBE_LON = float(os.getenv("NETWEATHER_RUSSIA_PROBE_LON", "37.62"))
DIAGNOSTIC_RESERVE_PERCENT = int(os.getenv("NETWEATHER_DIAGNOSTIC_RESERVE_PERCENT", "30"))
DIAGNOSTIC_COOLDOWN_SECONDS = int(os.getenv("NETWEATHER_DIAGNOSTIC_COOLDOWN_SECONDS", "900"))
DIAGNOSTIC_POLL_SECONDS = int(os.getenv("NETWEATHER_DIAGNOSTIC_POLL_SECONDS", "10"))
DIAGNOSTIC_MAX_POLL_ATTEMPTS = int(os.getenv("NETWEATHER_DIAGNOSTIC_MAX_POLL_ATTEMPTS", "30"))
OONI_ENABLED = os.getenv("NETWEATHER_OONI_ENABLED", "true").lower() in {"1","true","yes","on"}
OONI_BASE_URL = os.getenv("NETWEATHER_OONI_BASE_URL", "https://api.ooni.io/api/v1").rstrip("/")
OONI_PROBE_COUNTRY = os.getenv("NETWEATHER_OONI_PROBE_COUNTRY", "RU").strip().upper() or "RU"
IODA_ENABLED = os.getenv("NETWEATHER_IODA_ENABLED", "true").lower() in {"1","true","yes","on"}
IODA_BASE_URL = os.getenv("NETWEATHER_IODA_BASE_URL", "https://api.ioda.inetintel.cc.gatech.edu/v2").rstrip("/")
IODA_COUNTRY = os.getenv("NETWEATHER_IODA_COUNTRY", "RU").strip().upper() or "RU"
INTELLIGENCE_CACHE_SECONDS = int(os.getenv("NETWEATHER_INTELLIGENCE_CACHE_SECONDS", "21600"))
DEVICE_CODE_TTL_SECONDS = int(os.getenv("NETWEATHER_DEVICE_CODE_TTL_SECONDS", "600"))
DEVICE_POLL_INTERVAL_SECONDS = int(os.getenv("NETWEATHER_DEVICE_POLL_INTERVAL_SECONDS", "5"))
DEVICE_TOKEN_MAX_AGE_SECONDS = int(os.getenv("NETWEATHER_DEVICE_TOKEN_MAX_AGE_SECONDS", "31536000"))
DEVICE_AUTH_START_LIMIT = int(os.getenv("NETWEATHER_DEVICE_AUTH_START_LIMIT", "5"))
DEVICE_AUTH_START_WINDOW_SECONDS = int(os.getenv("NETWEATHER_DEVICE_AUTH_START_WINDOW_SECONDS", "3600"))

KNOWN_GROUPS = {
    "RUSSIAN": "Российские",
    "INTERNATIONAL": "Международные",
    "MESSENGERS": "Мессенджеры и соцсети",
    "INFRASTRUCTURE": "Инфраструктура",
    "CUSTOM": "Пользовательские",
}

DEFAULT_RESOURCES = [
    ("Яндекс", "https://yandex.ru", "RUSSIAN"),
    ("VK", "https://vk.com", "RUSSIAN"),
    ("Mail.ru", "https://mail.ru", "RUSSIAN"),
    ("GitHub", "https://github.com", "INTERNATIONAL"),
    ("Wikipedia", "https://www.wikipedia.org", "INTERNATIONAL"),
    ("Cloudflare", "https://www.cloudflare.com", "INFRASTRUCTURE"),
    ("Google", "https://www.google.com/generate_204", "INFRASTRUCTURE"),
    ("Telegram", "https://telegram.org", "MESSENGERS"),
]


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=2048)
    group_name: str = Field(default="CUSTOM", min_length=1, max_length=60)
    interval_seconds: int = Field(default=DEFAULT_INTERVAL, ge=30, le=86400)
    enabled: bool = True
    expected_status_min: int = Field(default=200, ge=100, le=599)
    expected_status_max: int = Field(default=399, ge=100, le=599)
    slow_threshold_ms: int = Field(default=1500, ge=100, le=120000)
    failure_threshold: int = Field(default=2, ge=1, le=10)
    alerts_enabled: bool = True


class CatalogAddRequest(BaseModel):
    resource_keys: list[str] = Field(min_length=1, max_length=40)


class OwnerLogin(BaseModel):
    password: str = Field(min_length=1, max_length=512)


class GroupCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    key: str | None = Field(default=None, max_length=60)
    color: str = Field(default="#3A8DFF", pattern=r"^#[0-9A-Fa-f]{6}$")


class GroupPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int | None = Field(default=None, ge=0, le=10000)


class ClientProbeResult(BaseModel):
    resource_id: int = Field(ge=1)
    status: str = Field(min_length=1, max_length=40)
    response_time_ms: int = Field(ge=0, le=300000)
    dns_ms: int | None = Field(default=None, ge=0, le=300000)
    tcp_ms: int | None = Field(default=None, ge=0, le=300000)
    tls_ms: int | None = Field(default=None, ge=0, le=300000)
    http_ms: int | None = Field(default=None, ge=0, le=300000)
    http_status: int | None = Field(default=None, ge=100, le=599)
    resolved_ip: str | None = Field(default=None, max_length=128)
    message: str = Field(default="", max_length=1000)


class ClientProbeRegistration(BaseModel):
    probe_key: str = Field(min_length=8, max_length=120)
    name: str = Field(default="Android", min_length=1, max_length=120)
    app_version: str = Field(default="", max_length=40)


class DeviceAuthorizationStart(BaseModel):
    device_id: str = Field(min_length=16, max_length=160, pattern=r"^[A-Za-z0-9._:-]+$")
    device_name: str = Field(default="Android", min_length=1, max_length=120)
    app_version: str = Field(default="", max_length=40)


class DeviceAuthorizationPoll(BaseModel):
    session_id: str = Field(min_length=20, max_length=160)
    poll_secret: str = Field(min_length=32, max_length=256)


class DeviceAuthorizationApprove(BaseModel):
    user_code: str = Field(min_length=6, max_length=16)


class ResourcePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    target: str | None = Field(default=None, min_length=1, max_length=2048)
    group_name: str | None = Field(default=None, min_length=1, max_length=60)
    interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    enabled: bool | None = None
    expected_status_min: int | None = Field(default=None, ge=100, le=599)
    expected_status_max: int | None = Field(default=None, ge=100, le=599)
    slow_threshold_ms: int | None = Field(default=None, ge=100, le=120000)
    failure_threshold: int | None = Field(default=None, ge=1, le=10)
    alerts_enabled: bool | None = None


def normalize_group(value: str) -> str:
    value = value.strip()
    if not value:
        return "CUSTOM"
    safe = re.sub(r"[^0-9A-Za-zА-Яа-яЁё _.-]", "", value)[:60].strip()
    return safe.upper() if safe.upper() in KNOWN_GROUPS else safe


def normalize_target(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Target must be a valid HTTP/HTTPS URL or hostname")
    if parsed.username or parsed.password:
        raise HTTPException(400, "Credentials in target URL are not allowed")
    return value
