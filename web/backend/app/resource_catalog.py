from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


CATALOG_AS_OF = "2026-08"
CATALOG_VERSION = "2026.08.1"


@dataclass(frozen=True)
class CatalogResource:
    key: str
    name: str
    target: str
    group_key: str
    rank: int
    aliases: tuple[str, ...] = ()
    note: str = ""

    @property
    def host(self) -> str:
        return (urlparse(self.target).hostname or "").lower().removeprefix("www.")

    def public(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "target": self.target,
            "group_key": self.group_key,
            "rank": self.rank,
            "aliases": list(self.aliases),
            "note": self.note,
        }


CATALOG_GROUPS = [
    {
        "key": "RUSSIAN",
        "title": "Российские сервисы",
        "color": "#35D89A",
        "source": "Similarweb · Россия / глобальный рейтинг",
        "as_of": "август 2026",
        "description": "Популярные российские сервисы без дублей с группой соцсетей.",
    },
    {
        "key": "INTERNATIONAL",
        "title": "Международные сервисы",
        "color": "#55C7FF",
        "source": "Similarweb · мировой web-трафик",
        "as_of": "август 2026",
        "description": "Популярные международные сайты без соцсетей и инфраструктурных провайдеров.",
    },
    {
        "key": "MESSENGERS",
        "title": "Мессенджеры и соцсети",
        "color": "#7C62FF",
        "source": "Similarweb · мировой web-трафик",
        "as_of": "август 2026",
        "description": "Крупнейшие социальные, видео- и коммуникационные платформы.",
    },
    {
        "key": "INFRASTRUCTURE",
        "title": "Инфраструктура",
        "color": "#FFAD4D",
        "source": "W3Techs · reverse proxy / CDN market share",
        "as_of": "сентябрь 2026",
        "description": "Крупные провайдеры CDN, reverse proxy и сетевой инфраструктуры.",
    },
]


CATALOG_RESOURCES: tuple[CatalogResource, ...] = (
    # Russian services. Social/video properties are intentionally assigned to MESSENGERS.
    CatalogResource("ru-yandex", "Яндекс", "https://yandex.ru", "RUSSIAN", 1, ("yandex.ru", "ya.ru")),
    CatalogResource("ru-dzen", "Дзен", "https://dzen.ru", "RUSSIAN", 2, ("dzen.ru",)),
    CatalogResource("ru-mail", "Mail.ru", "https://mail.ru", "RUSSIAN", 3, ("mail.ru",)),
    CatalogResource("ru-ozon", "Ozon", "https://www.ozon.ru", "RUSSIAN", 4, ("ozon.ru",)),
    CatalogResource("ru-avito", "Авито", "https://www.avito.ru", "RUSSIAN", 5, ("avito.ru",)),
    CatalogResource("ru-wb", "Wildberries", "https://www.wildberries.ru", "RUSSIAN", 6, ("wildberries.ru", "wb.ru")),
    CatalogResource("ru-gosuslugi", "Госуслуги", "https://www.gosuslugi.ru", "RUSSIAN", 7, ("gosuslugi.ru",)),
    CatalogResource("ru-rbc", "РБК", "https://www.rbc.ru", "RUSSIAN", 8, ("rbc.ru",)),
    CatalogResource("ru-kinopoisk", "Кинопоиск", "https://www.kinopoisk.ru", "RUSSIAN", 9, ("kinopoisk.ru",)),
    CatalogResource("ru-2gis", "2ГИС", "https://2gis.ru", "RUSSIAN", 10, ("2gis.ru",)),

    # Global traffic ranking, excluding services assigned to social/messaging.
    CatalogResource("int-google", "Google", "https://www.google.com/generate_204", "INTERNATIONAL", 1, ("google.com",)),
    CatalogResource("int-chatgpt", "ChatGPT", "https://chatgpt.com", "INTERNATIONAL", 2, ("chatgpt.com",)),
    CatalogResource("int-bing", "Bing", "https://www.bing.com", "INTERNATIONAL", 3, ("bing.com",)),
    CatalogResource("int-wikipedia", "Wikipedia", "https://www.wikipedia.org", "INTERNATIONAL", 4, ("wikipedia.org",)),
    CatalogResource("int-amazon", "Amazon", "https://www.amazon.com", "INTERNATIONAL", 5, ("amazon.com",)),
    CatalogResource("int-gemini", "Gemini", "https://gemini.google.com", "INTERNATIONAL", 6, ("gemini.google.com",)),
    CatalogResource("int-netflix", "Netflix", "https://www.netflix.com", "INTERNATIONAL", 7, ("netflix.com",)),
    CatalogResource("int-microsoft", "Microsoft", "https://www.microsoft.com", "INTERNATIONAL", 8, ("microsoft.com",)),
    CatalogResource("int-github", "GitHub", "https://github.com", "INTERNATIONAL", 9, ("github.com",)),
    CatalogResource("int-apple", "Apple", "https://www.apple.com", "INTERNATIONAL", 10, ("apple.com",)),

    # Global social / communications traffic.
    CatalogResource("msg-youtube", "YouTube", "https://www.youtube.com", "MESSENGERS", 1, ("youtube.com", "youtu.be")),
    CatalogResource("msg-facebook", "Facebook", "https://www.facebook.com", "MESSENGERS", 2, ("facebook.com",)),
    CatalogResource("msg-instagram", "Instagram", "https://www.instagram.com", "MESSENGERS", 3, ("instagram.com",)),
    CatalogResource("msg-x", "X", "https://x.com", "MESSENGERS", 4, ("x.com", "twitter.com")),
    CatalogResource("msg-reddit", "Reddit", "https://www.reddit.com", "MESSENGERS", 5, ("reddit.com",)),
    CatalogResource("msg-tiktok", "TikTok", "https://www.tiktok.com", "MESSENGERS", 6, ("tiktok.com",)),
    CatalogResource("msg-whatsapp", "WhatsApp", "https://www.whatsapp.com", "MESSENGERS", 7, ("whatsapp.com", "web.whatsapp.com")),
    CatalogResource("msg-vk", "VK", "https://vk.ru", "MESSENGERS", 8, ("vk.ru", "vk.com")),
    CatalogResource("msg-telegram", "Telegram", "https://telegram.org", "MESSENGERS", 9, ("telegram.org", "t.me")),
    CatalogResource("msg-discord", "Discord", "https://discord.com", "MESSENGERS", 10, ("discord.com",)),

    # W3Techs reverse-proxy/CDN ranking, September 2026.
    CatalogResource("infra-cloudflare", "Cloudflare", "https://www.cloudflare.com", "INFRASTRUCTURE", 1, ("cloudflare.com", "1.1.1.1")),
    CatalogResource("infra-cloudfront", "Amazon CloudFront", "https://aws.amazon.com/cloudfront/", "INFRASTRUCTURE", 2, ("aws.amazon.com", "cloudfront.net")),
    CatalogResource("infra-fastly", "Fastly", "https://www.fastly.com", "INFRASTRUCTURE", 3, ("fastly.com",)),
    CatalogResource("infra-ddosguard", "DDoS-Guard", "https://ddos-guard.net", "INFRASTRUCTURE", 4, ("ddos-guard.net",)),
    CatalogResource("infra-akamai", "Akamai", "https://www.akamai.com", "INFRASTRUCTURE", 5, ("akamai.com",)),
    CatalogResource("infra-sucuri", "Sucuri", "https://sucuri.net", "INFRASTRUCTURE", 6, ("sucuri.net",)),
    CatalogResource("infra-imperva", "Imperva", "https://www.imperva.com", "INFRASTRUCTURE", 7, ("imperva.com",)),
    CatalogResource("infra-azion", "Azion", "https://www.azion.com", "INFRASTRUCTURE", 8, ("azion.com",)),
    CatalogResource("infra-bunny", "Bunny CDN", "https://bunny.net", "INFRASTRUCTURE", 9, ("bunny.net",)),
    CatalogResource("infra-arvancloud", "ArvanCloud", "https://www.arvancloud.ir/en", "INFRASTRUCTURE", 10, ("arvancloud.ir",)),
)


CATALOG_BY_KEY = {item.key: item for item in CATALOG_RESOURCES}


def canonical_host(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    return (parsed.hostname or "").lower().rstrip(".").removeprefix("www.")


def catalog_match(value: str) -> CatalogResource | None:
    host = canonical_host(value)
    if not host:
        return None
    for item in CATALOG_RESOURCES:
        candidates = {item.host, *(x.lower().removeprefix("www.") for x in item.aliases)}
        if host in candidates:
            return item
    return None


def catalog_payload(existing_keys: set[str] | None = None) -> dict:
    existing_keys = existing_keys or set()
    groups = []
    for group in CATALOG_GROUPS:
        items = [
            {**item.public(), "already_added": item.key in existing_keys}
            for item in CATALOG_RESOURCES
            if item.group_key == group["key"]
        ]
        groups.append({**group, "items": items})
    return {
        "version": CATALOG_VERSION,
        "as_of": CATALOG_AS_OF,
        "groups": groups,
    }
