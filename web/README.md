# NetWeather Web

Web-контур NetWeather для `netweather.online`. Проверки выполняются на VPS, а браузер отображает агрегированное состояние, историю и поэтапную диагностику DNS → TCP → TLS → HTTP.

## Что уже реализовано

- Реальные проверки HTTP/HTTPS-ресурсов с VPS.
- DNS, TCP, TLS и HTTP тайминги.
- Индекс доступности и режимы NetWeather по логике Android-приложения.
- Фоновый планировщик с индивидуальным интервалом от 30 секунд.
- SQLite + WAL и хранение истории за 30 дней.
- Графики доступности и задержки.
- Группы ресурсов: российские, международные, пользовательские.
- Ручная проверка одного ресурса и всех ресурсов.
- Современный responsive UI для desktop/mobile.
- Dark/light theme.
- Bearer-токен для операций изменения конфигурации.
- Блокировка private/loopback/link-local целей по умолчанию.
- Docker Compose + Caddy + автоматический HTTPS.

## Быстрый запуск на VPS

Требования: Docker Engine и Docker Compose plugin.

```bash
git clone https://github.com/OvodokSP/NetWeather.git
cd NetWeather
git checkout feature/web-vps-monitoring
cd web
cp .env.example .env
```

Создайте длинный случайный токен и поместите его в `.env`:

```bash
openssl rand -hex 32
nano .env
```

Запуск:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f --tail=100
```

Проверка API локально на сервере:

```bash
curl -fsS https://netweather.online/api/health
```

Ожидаемый ответ:

```json
{"status":"ok","time":...}
```

## DNS домена

У регистратора домена должны быть созданы записи:

- `A` для `netweather.online` → публичный IPv4 VPS.
- `A` для `www.netweather.online` → публичный IPv4 VPS.
- При наличии IPv6 можно дополнительно создать `AAAA`.

На VPS должны быть доступны входящие TCP 80 и 443. Caddy автоматически получает и обновляет TLS-сертификаты после корректного DNS-разрешения домена.

## Управление

Публичные GET-endpoint'ы позволяют отображать состояние без авторизации. Создание, изменение, удаление ресурсов и принудительные проверки требуют `NETWEATHER_API_TOKEN`.

В UI нажмите `API-токен` и вставьте значение из `.env`. Токен сохраняется только в `localStorage` браузера.

## API

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/resources`
- `POST /api/resources`
- `PATCH /api/resources/{id}`
- `DELETE /api/resources/{id}`
- `POST /api/resources/{id}/check`
- `POST /api/check-all`
- `GET /api/history?hours=24`

Для write-запросов:

```http
Authorization: Bearer <NETWEATHER_API_TOKEN>
```

## Безопасность

`ALLOW_PRIVATE_TARGETS=false` оставляйте значением по умолчанию для публичного сайта. Это запрещает проверку loopback, link-local и private IP и снижает риск использования NetWeather как SSRF-инструмента.

Если позже понадобится мониторинг внутренних сервисов, его лучше реализовать через отдельный приватный probe/agent, а не открывать private targets на публичном API.

## Архитектура

```text
Internet
   │
   ▼
Caddy :443
   │
   ▼
FastAPI / NetWeather monitor
   ├── scheduler
   ├── DNS/TCP/TLS/HTTP diagnostics
   ├── SQLite history
   └── static web UI
```

Один worker Uvicorn выбран намеренно: планировщик находится внутри процесса приложения. При горизонтальном масштабировании scheduler нужно вынести в отдельный worker/queue, чтобы избежать дублирования проверок.
