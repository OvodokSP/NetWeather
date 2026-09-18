# NetWeather

> **Погода для интернета:** единый интерфейс, который показывает не только *работает ли ресурс*, но и *где начинается проблема* — у самого ресурса, на внешнем маршруте, в российском контуре, у оператора или в локальной сети пользователя.

[![Web checks](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml)
[![Android build](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml)

**Рабочий сайт:** https://netweather.online  
**Текущий web-контур:** `0.3.10-web`  
**Статус:** активная разработка; интерфейс и диагностика стабилизируются до введения аккаунтов/тарифов.

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

- современный dashboard без обязательной авторизации в development-контуре;
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
- capability-aware UI: недоступные панели не занимают место;
- минимальный размер текста в web UI — **10 px**;
- hardened production container и закрытый deployment channel.

### Android

Android-клиент остаётся частью общей архитектуры и развивается как Native Probe:

- локальные проверки;
- история;
- фоновые задачи;
- уведомления;
- виджеты;
- интеграция с общей моделью NetWeather Probe.

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
- полезная плотность вместо пустого пространства;
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
