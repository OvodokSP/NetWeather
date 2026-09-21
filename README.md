# NetWeather

> **Погода для интернета:** сервис без обязательного пользовательского оборудования, который показывает глобальное состояние ресурсов и, при подключённом Android-приложении, состояние вашей сети.

[![Web checks](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml)
[![Android build](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml)
[![Auto-deploy](https://github.com/OvodokSP/NetWeather/actions/workflows/deploy-web.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/deploy-web.yml)
[![Android preview](https://github.com/OvodokSP/NetWeather/actions/workflows/release.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/release.yml)

| Контур | Состояние |
|---|---|
| Web | [netweather.online](https://netweather.online), `0.4.1-web` после успешного auto-deploy |
| Android | `0.4.1-alpha`; новый APK публикуется только после зелёного Android CI |
| Источники | VPS baseline, событийные Globalping/OONI/IODA/официальные Statuspage-ленты и необязательный авторизованный Android local probe |

## Что такое NetWeather

NetWeather объединяет hosted-мониторинг и необязательные software probes в одну картину сети.

- **Global State** — VPS: DNS → TCP → TLS → HTTP, история и серверная диагностика.
- **External evidence** — Globalping, cached OONI/IODA и официальные статусы GitHub/Cloudflare при инциденте или ручной диагностике.
- **Your Network** — необязательная локальная диагностика Android без root, VPN, ADB и отдельного hardware.
- **Incident Assessment** — детерминированный вывод с уровнем уверенности и честным `UNKNOWN` при нехватке данных.

Ключевой принцип продукта: **ничего устанавливать не обязательно; Android только повышает глубину диагностики вашей сети.**

## Что уже работает

### Web

- публичный dashboard для чтения и защищённая сессия владельца для управляющих действий;
- группы ресурсов;
- каталог популярных ресурсов с дедупликацией;
- пользовательские ресурсы;
- массовое добавление ресурсов;
- глобальная доступность и история;
- DNS/TCP/TLS/HTTP этапы;
- события и инциденты;
- read/unread для инцидентов;
- лента доказательств по ресурсу: проверки, инциденты, Globalping и внешние сигналы (до 12 месяцев);
- диагностика и server-side traceroute;
- настраиваемый Overview и закреплённые ресурсы;
- problem-first Overview: здоровье, свежесть данных, доступные ресурсы, типичный отклик, график, события и быстрый фильтр проблем;
- естественная прокрутка Overview без обрезания таблицы и с читаемыми карточками на desktop/mobile;
- capability-aware UI: недоступные панели не занимают место;
- `GET /api/capabilities` публикует бесплатные функции, owner-only controls и отключённые до billing платные проверки;
- минимальный размер текста в web UI — **10 px**;
- hardened production container и закрытый deployment channel;
- каталоговые сервисы с anti-bot HTTP-ответом не создают ложные инциденты, если DNS/TCP/TLS и HTTP-обмен состоялись.

### Android

Android-клиент использует общий backend как источник ресурсов и глобального состояния и одновременно остаётся optional local probe:

- локальные проверки;
- история;
- фоновые задачи;
- уведомления;
- виджеты;
- интеграция с общей моделью NetWeather Probe.

Установочная alpha-preview сборка 0.4.1 публикуется в [GitHub Releases](https://github.com/OvodokSP/NetWeather/releases/tag/android-v0.4.1-alpha-preview.1) после успешного CI. Это debug-signed APK для проверки, а не production-signed релиз; точные ограничения описаны в [docs/ANDROID_PREVIEW.md](docs/ANDROID_PREVIEW.md).

## Архитектура репозитория

```text
NetWeather/
├── app/                    Android / Native Probe
├── web/
│   ├── backend/            FastAPI, SQLite, monitoring core
│   ├── frontend/           dashboard UI
│   └── deploy/             smoke и security boundary
├── docs/
│   ├── ARCHITECTURE.md     модель probes и поток данных
│   ├── UI_GUIDELINES.md    контракт интерфейса
│   └── PROJECT_STATUS.md   текущая контрольная точка
├── .github/workflows/      CI/CD
├── ROADMAP.md
├── SECURITY.md
└── CHANGELOG.md
```

## Безопасность production

NetWeather на VPS рассматривается как **потенциально недоверенное приложение** и отделён от остальных сервисов:

- container user `10001:10001`;
- read-only root filesystem;
- `CAP_DROP=ALL`;
- `no-new-privileges`;
- без Docker socket;
- без bind-mount файлов хоста;
- записывается только отдельный volume `/data`;
- отдельная Docker-сеть;
- nftables запрещает NetWeather инициировать соединения к VPS, RFC1918, VPN/CGNAT и link-local сетям;
- production image собирается вне VPS;
- deployment SSH key — forced-command only.

Подробности: [SECURITY.md](SECURITY.md).

## Разработка

Web checks:

```bash
python -m py_compile web/backend/app/*.py
node --check web/frontend/assets/dashboard.js
PYTHONPATH=web/backend python -m unittest discover -s web/backend/tests -v
```

Android:

```bash
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

## Принципы UI

- единый визуальный язык на всех экранах;
- шрифт не меньше 10 px;
- полезная плотность без сжатия, обрезания и конкурирующих областей прокрутки;
- группы — часть основной модели, а не вспомогательный фильтр;
- недоступный функционал скрывается, а не показывается мёртвым;
- действия имеют loading/success/error состояния;
- окна должны одинаково работать мышью и клавиатурой;
- опасные действия требуют явного подтверждения.

Подробности: [docs/UI_GUIDELINES.md](docs/UI_GUIDELINES.md).

## Roadmap

Остаются: live-provider smoke из production, QA на реальных Android-устройствах, backup/restore rehearsal и production-подпись Android (для неё ещё не настроен signing key). Публичные Statuspage-ленты GitHub/Cloudflare, evidence timeline и capability registry уже добавлены. Аппаратные router probes в roadmap не входят.

См. [ROADMAP.md](ROADMAP.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
