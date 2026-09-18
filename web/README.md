# NetWeather Web

NetWeather Web — VPS-first монитор доступности интернет-ресурсов для `netweather.online`. Все сетевые проверки выполняются на VPS, браузер получает готовые измерения, историю и события.

## Версия 0.3.0-web

- DNS → TCP → TLS → HTTP диагностика с отдельными таймингами каждого этапа.
- Индекс доступности, режимы сети и группировка ресурсов.
- Стартовый набор из 8 ресурсов создаётся автоматически только для пустой БД.
- Любые пользовательские группы и HTTP/HTTPS-цели.
- История за 30 дней и графики доступности/задержки.
- Контроль срока TLS-сертификата.
- Триггеры: N последовательных ошибок, медленный ответ, истечение TLS.
- Журнал активных/закрытых инцидентов и подтверждение тревог.
- Browser Notifications; опциональный серверный JSON webhook через `ALERT_WEBHOOK_URL`.
- Ручная проверка одной цели или всех целей.
- Traceroute до публичной цели из VPS-контейнера.
- Карточка ресурса с последними проверками, IP, HTTP, задержкой и TLS.
- Защита от SSRF: private/loopback/link-local/reserved targets блокируются; HTTP redirects автоматически не следуются.
- Responsive dark/light UI без внешних JS/CSS CDN.
- HEAD для корня поддерживается, поэтому стандартные uptime-проверки не получают 405.


## Двухконтурная модель

Один зарубежный VPS не может отличить блокировку внутри РФ от обычной доступности ресурса снаружи. Поэтому 0.3.0 использует две независимые точки наблюдения:

- `EXTERNAL / VPS_EU` — внешний VPS: отвечает на вопрос «ресурс вообще жив?».
- `DOMESTIC / RU_HOME` — probe внутри российского контура: отвечает на вопрос «ресурс доступен из сети РФ?».

Классификация:

| Внешний VPS | Российский probe | Вывод |
| --- | --- | --- |
| OK | OK | Доступен |
| OK | ошибка | Вероятное ограничение / региональная проблема |
| ошибка | ошибка | Вероятное падение ресурса |
| ошибка | OK | Проблема внешнего маршрута/VPS |
| любой | нет свежих данных | Недостаточно данных; вывод о блокировке запрещён |

Один российский probe даёт полезную, но не абсолютную классификацию. Для высокой уверенности архитектура допускает несколько DOMESTIC probe у разных провайдеров.

### Важное требование к домашнему probe

Трафик probe должен идти **напрямую через российского ISP**, минуя HRNeo, AmneziaWG, VLESS и другие обходные маршруты. Иначе NetWeather будет измерять уже «исправленный» маршрут и не увидит ограничение.


## Production-схема

```text
Internet
   │
   ▼
nginx :80/:443 на VPS 31.77.56.66
   │
   ▼
127.0.0.1:18081
   │
   ▼
NetWeather container :8000
   ├── scheduler
   ├── DNS / TCP / TLS / HTTP
   ├── traceroute
   ├── incidents / triggers
   ├── SQLite WAL
   └── static web UI
```

`127.0.0.1:18080` на текущем VPS занят другим сервисом, поэтому NetWeather использует `18081`.

## Обновление на VPS

Существующий `.env` не перезаписывать.

```bash
cd /opt/NetWeather
git checkout feature/web-vps-monitoring
git pull --ff-only origin feature/web-vps-monitoring
cd web
docker compose up -d --build
```

Для новых установок:

```env
NETWEATHER_API_TOKEN=<long-random-secret>
DEFAULT_INTERVAL_SECONDS=60
REQUEST_TIMEOUT_SECONDS=8
ALLOW_PRIVATE_TARGETS=false
NETWEATHER_SEED_DEFAULTS=true
ALERT_WEBHOOK_URL=
NETWEATHER_BIND_PORT=18081
```

`ALERT_WEBHOOK_URL` необязателен. Если указан, NetWeather отправляет JSON при открытии/закрытии инцидентов.

## Проверка после обновления

```bash
cd /opt/NetWeather/web
chmod +x deploy/smoke-test.sh
docker compose ps
curl -fsS http://127.0.0.1:18081/api/health
./deploy/smoke-test.sh
```

Smoke test проверяет:
- health/system/dashboard/groups/resources/incidents/history;
- HEAD и frontend;
- CRUD временного ресурса;
- ручную проверку;
- traceroute;
- check-all;
- удаление временной цели.

## Как работают тревоги

У каждого ресурса есть:
- `failure_threshold` — сколько последовательных неуспешных проверок открывает DOWN incident;
- `slow_threshold_ms` — порог SLOW incident;
- `alerts_enabled` — включение триггеров для цели;
- TLS expiry trigger при остатке <= 14 дней.

DOWN автоматически закрывается после восстановления. События хранятся в SQLite; активные можно подтвердить через UI.

## API

Публичные:
- `GET /api/health`
- `GET /api/system`
- `GET /api/dashboard`
- `GET /api/groups`
- `GET /api/resources`
- `GET /api/resources/{id}`
- `GET /api/incidents`
- `GET /api/history?hours=24`

С Bearer token:
- `POST /api/resources`
- `PATCH /api/resources/{id}`
- `DELETE /api/resources/{id}`
- `POST /api/resources/{id}/check`
- `POST /api/resources/{id}/trace`
- `POST /api/check-all`
- `POST /api/incidents/{id}/ack`

## Nginx / TLS

Готовый vhost: `deploy/nginx-netweather.conf`. Upstream должен оставаться `127.0.0.1:18081`.

```bash
nginx -t && systemctl reload nginx
```

TLS выпускается и обновляется Certbot на хосте.


## Российский probe на Keenetic

Скрипт: `deploy/keenetic/netweather-probe.sh`.

На сервере сначала задайте отдельный токен:

```bash
cd /opt/NetWeather/web
printf '\nNETWEATHER_AGENT_TOKEN=%s\n' "$(openssl rand -hex 32)" >> .env
docker compose up -d --build
```

Токен для probe смотрится локально на сервере:

```bash
grep '^NETWEATHER_AGENT_TOKEN=' .env
```

На Keenetic/Entware агент использует `curl`, `awk`, `sed` и `traceroute`. Перед постоянным запуском обязательно подтвердите, что его запросы выходят через прямой WAN российского провайдера, а не через HRNeo/AWG.

Агент:
- получает актуальный список целей с `/api/agent/config.tsv`;
- измеряет DNS/TCP/TLS/HTTP через curl timings;
- отправляет результат в `/api/agent/result`;
- принимает задания российского traceroute;
- heartbeat автоматически отражается в UI.
