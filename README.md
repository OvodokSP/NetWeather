# NetWeather

> **Погода для интернета:** единый интерфейс, который показывает не только *работает ли ресурс*, но и *где начинается проблема* — у самого ресурса, на внешнем маршруте, в российском контуре, у оператора или в локальной сети пользователя.

[![Web checks](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/web-checks.yml)
[![Android build](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/build.yml)
[![Auto-deploy](https://github.com/OvodokSP/NetWeather/actions/workflows/deploy-web.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/deploy-web.yml)
[![Android preview](https://github.com/OvodokSP/NetWeather/actions/workflows/release.yml/badge.svg?branch=feature%2Fweb-vps-monitoring)](https://github.com/OvodokSP/NetWeather/actions/workflows/release.yml)

| Контур | Состояние |
|---|---|
| Web | [netweather.online](https://netweather.online), `0.4.1-web` |
| Android | `0.4.1-alpha` preview APK, debug-signed; см. [GitHub Releases](https://github.com/OvodokSP/NetWeather/releases) |
| Probes | VPS (`GLOBAL`), публичные Globalping-точки РФ (`RUSSIA`) и необязательное Android-устройство (`USER`) |

## Что такое NetWeather

NetWeather объединяет независимые источники измерений в одну картину сети. Сервис работает без домашнего роутера, Keenetic, Entware или другого пользовательского оборудования.

- **GLOBAL** — VPS-проверки DNS → TCP → TLS → HTTP; расширенные Globalping-измерения запускаются по событию или вручную.
- **RUSSIA** — независимые публичные Globalping-точки в РФ. Недостаточные данные показываются как «нет данных», а не как подтверждённая блокировка.
- **USER** — необязательные локальные измерения Android после сопряжения устройства с сайтом.
- Вывод о причине сбоя строится только по полученным измерениям; локальная сеть и оператор не угадываются без соответствующих данных.

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
- диагностика, инциденты и история измерений;
- настраиваемый Overview и закреплённые ресурсы;
- problem-first Overview: здоровье, свежесть данных, доступные ресурсы, типичный отклик, график, события и быстрый фильтр проблем;
- естественная прокрутка Overview без обрезания таблицы и с читаемыми карточками на desktop/mobile;
- capability-aware UI: недоступные панели не занимают место;
- минимальный размер текста в web UI — **10 px**;
- hardened production container и закрытый deployment channel;
- каталоговые сервисы с anti-bot HTTP-ответом не создают ложные инциденты, если DNS/TCP/TLS и HTTP-обмен состоялись.

### Android

Android-клиент — необязательный локальный probe и работает с тем же каталогом ресурсов:

- локальные проверки;
- история;
- фоновые задачи;
- уведомления;
- виджеты;
- сопряжение с сайтом одноразовым кодом;
- отправка локальных измерений после явного сопряжения.

Preview-сборки автоматически публикуются в [GitHub Releases](https://github.com/OvodokSP/NetWeather/releases). Это debug-сборки, не production-signed релиз; ограничения описаны в [docs/ANDROID_PREVIEW.md](docs/ANDROID_PREVIEW.md).

## Архитектура репозитория

```text
NetWeather/
├── app/                    Android / Native Probe
├── web/
│   ├── backend/            FastAPI, SQLite, monitoring core
│   ├── frontend/           dashboard UI
│   └── deploy/             smoke test и security boundary
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

Оставшиеся этапы:

1. проверить pairing и адаптивность на реальных Android-устройствах;
2. сохранить подтверждённые live-ответы Globalping/OONI/IODA как регрессионные fixtures;
3. провести репетицию backup/restore на копии данных;
4. настроить production signing для Android;
5. отдельно решить, когда включать платные глубокие проверки и биллинг.

См. [ROADMAP.md](ROADMAP.md).

## Лицензия

MIT — см. [LICENSE](LICENSE).
