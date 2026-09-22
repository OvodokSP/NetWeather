# NetWeather

> **Погода для интернета:** единый интерфейс, который показывает не только *работает ли ресурс*, но и *где начинается проблема* — у самого ресурса, на внешнем маршруте, в российском контуре, у оператора или в локальной сети пользователя.

[![Web checks](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml)
[![Android build](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml)
[![Auto-deploy](https://github.com/OvodokSP/NetWeather/actions/workflows/deploy-web.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/deploy-web.yml)
[![Android preview](https://github.com/OvodokSP/NetWeather/actions/workflows/release.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/release.yml)

| Контур | Состояние |
|---|---|
| Web | [netweather.online](https://netweather.online), `0.3.10-web` |
| Android | [alpha-preview APK и SHA-256](https://github.com/OvodokSP/NetWeather/releases/tag/android-v0.1.0-alpha-preview.1) |
| Probes | Global Probe работает; Domestic/Browser Probe и единый fault-domain находятся в разработке |

## Что такое NetWeather

NetWeather объединяет несколько точек наблюдения в одну картину сети.

- **Global Probe** — внешний VPS: DNS → TCP → TLS → HTTP, история и серверная диагностика.
- **Domestic Probe** — российская точка наблюдения: сравнение доступности из внутреннего контура.
- **Browser Probe** — следующий основной этап: проверка доступности через фактическое соединение посетителя без установки ПО.
- **Native Probe** — Android / router probe для глубокой локальной диагностики и traceroute.
- **Fault Domain** — сведение результатов probes в понятный вывод: где именно начинается отказ.

Ключевой принцип продукта: **ничего устанавливать не обязательно; установка probe только повышает глубину и доказательность диагностики.**

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
- диагностика и server-side traceroute;
- настраиваемый Overview и закреплённые ресурсы;
- problem-first Overview: здоровье, свежесть данных, доступные ресурсы, типичный отклик, график, события и быстрый фильтр проблем;
- естественная прокрутка Overview без обрезания таблицы и с читаемыми карточками на desktop/mobile;
- capability-aware UI: недоступные панели не занимают место;
- минимальный размер текста в web UI — **10 px**;
- hardened production container и закрытый deployment channel;
- каталоговые сервисы с anti-bot HTTP-ответом не создают ложные инциденты, если DNS/TCP/TLS и HTTP-обмен состоялись.

### Android

Android-клиент остаётся частью общей архитектуры и развивается как Native Probe:

- локальные проверки;
- история;
- фоновые задачи;
- уведомления;
- виджеты;
- интеграция с общей моделью NetWeather Probe.

Установочная alpha-preview сборка публикуется в [GitHub Releases](https://github.com/OvodokSP/NetWeather/releases/tag/android-v0.1.0-alpha-preview.1). Это подписанный debug APK для проверки, а не production-signed релиз; точные ограничения описаны в [docs/ANDROID_PREVIEW.md](docs/ANDROID_PREVIEW.md).

## Архитектура репозитория

```text
NetWeather/
├── app/                    Android / Native Probe
├── web/
│   ├── backend/            FastAPI, SQLite, monitoring core
│   ├── frontend/           dashboard UI
│   └── deploy/             smoke, Keenetic probe, security boundary
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

Ближайший продуктовый контур:

1. polish web UI и interaction contract;
2. Keenetic как постоянный Domestic Probe;
3. Browser Probe;
4. сравнение `GLOBAL ↔ DOMESTIC ↔ USER`;
5. fault-domain engine;
6. только после полезного рабочего инструмента — аккаунты, права, лицензии и capability-тарифы.

См. [ROADMAP.md](ROADMAP.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
