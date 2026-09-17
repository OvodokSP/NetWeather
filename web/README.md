# NetWeather Web

Web-контур NetWeather для `netweather.online`. Проверки выполняются на VPS, браузер отображает агрегированное состояние, историю и поэтапную диагностику DNS → TCP → TLS → HTTP.

## Что реализовано

- Реальные HTTP/HTTPS-проверки с VPS.
- DNS, TCP, TLS и HTTP тайминги.
- Индекс доступности и режимы NetWeather по логике Android-приложения.
- Фоновый планировщик с индивидуальным интервалом от 30 секунд.
- SQLite + WAL и история за 30 дней.
- Графики доступности и задержки.
- Группы ресурсов: российские, международные, пользовательские.
- Ручная проверка одного ресурса и всех ресурсов.
- Responsive desktop/mobile UI, dark/light theme.
- Bearer-токен для изменения конфигурации.
- Блокировка private/loopback/link-local целей по умолчанию.

## Production-схема для текущего VPS

На VPS уже работает системный nginx на 80/443, поэтому NetWeather **не запускает собственный Caddy** и не публикует контейнер наружу. Приложение слушает только loopback:

```text
Internet
   │
   ▼
nginx :80/:443 (host)
   │
   ▼
127.0.0.1:18080
   │
   ▼
NetWeather container :8000
   ├── scheduler
   ├── DNS/TCP/TLS/HTTP diagnostics
   ├── SQLite history
   └── static web UI
```

## DNS

Для production у домена должен остаться **один** A-record:

- `netweather.online` → `31.77.56.66`
- `www.netweather.online` → CNAME `netweather.online`

Старые A-records на другие IP необходимо удалить, иначе запросы и ACME-проверки могут попадать на другой сервер.

## Установка

```bash
cd /opt
sudo git clone https://github.com/OvodokSP/NetWeather.git
cd /opt/NetWeather
git checkout feature/web-vps-monitoring
cd web
cp .env.example .env
openssl rand -hex 32
nano .env
```

В `.env`:

```env
NETWEATHER_API_TOKEN=<случайный секрет>
DEFAULT_INTERVAL_SECONDS=60
REQUEST_TIMEOUT_SECONDS=8
ALLOW_PRIVATE_TARGETS=false
NETWEATHER_BIND_PORT=18080
```

Запуск контейнера:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:18080/api/health
```

## Подключение к существующему nginx

Готовый server block лежит в `deploy/nginx-netweather.conf`.

```bash
sudo cp deploy/nginx-netweather.conf /etc/nginx/sites-available/netweather.online
sudo ln -sfn /etc/nginx/sites-available/netweather.online /etc/nginx/sites-enabled/netweather.online
sudo nginx -t
sudo systemctl reload nginx
```

Проверка HTTP до выпуска сертификата:

```bash
curl -I http://netweather.online/
curl -fsS http://netweather.online/api/health
```

Для TLS используйте уже принятый на VPS способ выпуска сертификатов. Если установлен Certbot с nginx plugin:

```bash
sudo certbot --nginx -d netweather.online -d www.netweather.online
```

После этого:

```bash
curl -fsS https://netweather.online/api/health
```

Ожидаемый ответ:

```json
{"status":"ok","time":...}
```

## Управление

Публичные GET endpoint'ы отображают состояние без авторизации. Создание, изменение и удаление ресурсов, а также принудительные проверки требуют `NETWEATHER_API_TOKEN`.

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

`ALLOW_PRIVATE_TARGETS=false` оставлять значением по умолчанию для публичного сайта. Это блокирует loopback, link-local и private IP и снижает риск SSRF.

Если понадобится мониторинг внутренних сервисов, его следует вынести в отдельный приватный probe/agent.

Один worker Uvicorn выбран намеренно: scheduler находится внутри процесса приложения. При горизонтальном масштабировании scheduler нужно вынести в отдельный worker/queue.
