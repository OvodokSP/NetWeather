from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException
from pydantic import BaseModel, Field

APP_VERSION = "0.3.1-web"
STARTED_AT = int(time.time())
DB_PATH = Path(os.getenv("NETWEATHER_DB", "/data/netweather.db"))
API_TOKEN = os.getenv("NETWEATHER_API_TOKEN", "")
ALLOW_PRIVATE_TARGETS = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"
DEFAULT_INTERVAL = int(os.getenv("DEFAULT_INTERVAL_SECONDS", "60"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "8"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))
SEED_DEFAULTS = os.getenv("NETWEATHER_SEED_DEFAULTS", "true").lower() == "true"
SCHEDULER_ENABLED = os.getenv("NETWEATHER_SCHEDULER_ENABLED", "true").lower() == "true"
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()
AGENT_TOKEN = os.getenv("NETWEATHER_AGENT_TOKEN", "").strip()
AGENT_STALE_SECONDS = int(os.getenv("NETWEATHER_AGENT_STALE_SECONDS", "180"))
SERVER_PROBE_KEY = os.getenv("NETWEATHER_SERVER_PROBE_KEY", "VPS_EU").strip() or "VPS_EU"
SERVER_PROBE_NAME = os.getenv("NETWEATHER_SERVER_PROBE_NAME", "Внешний VPS").strip() or "Внешний VPS"

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


class AgentResult(BaseModel):
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
