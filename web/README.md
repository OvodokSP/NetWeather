# NetWeather Web

NetWeather Web — hardware-free сервис наблюдения за доступностью ресурсов. Базовые проверки выполняет изолированный VPS-контейнер; дополнительные глобальные измерения может запросить внешний provider, а Android-приложение служит необязательным software probe для сети пользователя.

**Текущая линия:** `0.4.0-web`.

## Production boundary

Production не запускается обычным `docker compose up` из рабочего дерева. Образ проверяется и собирается GitHub Actions, передаётся по forced-command SSH и запускается root-owned helper с фиксированным security profile. Данные находятся в отдельном Docker volume и сохраняются при замене образа и rollback.

См. [DEPLOYMENT.md](DEPLOYMENT.md) и [../SECURITY.md](../SECURITY.md).

## Компоненты

```text
web/
├── backend/               FastAPI, scheduler, SQLite, diagnostics
├── frontend/              responsive dashboard
├── deploy/security/       host-enforced production boundary
├── deploy/smoke-test.sh   runtime smoke
├── Dockerfile
└── docker-compose.yml     local hardened profile
```

## Измерения и выводы

- **GLOBAL STATE** — наблюдения VPS и, при включении, внешнего measurement provider.
- **YOUR NETWORK** — свежие измерения Android-приложения; без приложения показывается честное состояние «нет данных».
- Старые router measurements сохраняются как `LEGACY`, но не участвуют в текущей диагностике.
- Диагноз строится только из доступных evidence и возвращает одну из фиксированных классификаций: `OK`, `SERVICE_DOWN`, `DEGRADED`, `LOCAL_NETWORK`, `ISP_OUTAGE`, `DNS_FAILURE`, `ROUTING_FAILURE`, `REGIONAL_OUTAGE`, `POSSIBLE_FILTERING`, `UNKNOWN`.

Globalping выключен по умолчанию. При включении действуют приоритеты, cooldown/dedup и резерв квоты; здоровые ресурсы не запускают глубокую диагностику.

## Resource и UI contract

- группы и канонические ресурсы сохраняют идентичность;
- пользователь может добавить публичный HTTP/HTTPS-ресурс из popup поиска;
- платные/глубокие проверки и административные изменения защищены;
- результаты поиска накладываются поверх dashboard и не меняют геометрию страницы;
- интерфейс адаптируется от узкого телефона до desktop и не маскирует отсутствие данных.

Полный UI-контракт: [../docs/UI_GUIDELINES.md](../docs/UI_GUIDELINES.md).

## Локальные проверки

```bash
python -m py_compile backend/app/*.py
node --check frontend/assets/dashboard.js
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
bash -n deploy/smoke-test.sh
```

## Auto-deploy

`.github/workflows/deploy-web.yml` выполняет verify, сборку hardened image, runtime smoke, безопасную доставку immutable image и post-deploy assertions. Деплой активен только при repository variable `NETWEATHER_DEPLOY_ENABLED=true`; `[no-deploy]` в сообщении maintenance-коммита отключает доставку.

Production runtime: UID/GID `10001`, read-only rootfs, `CAP_DROP=ALL`, `no-new-privileges`, без Docker socket и host bind mounts, с единственной writable областью `/data`. Egress к host/private/VPN подсетям блокируется host policy.

Production secrets принадлежат root и хранятся в `/etc/netweather/netweather.env`; их нельзя добавлять в репозиторий или рабочий каталог.
