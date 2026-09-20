# NetWeather Web

Web-контур NetWeather объединяет мониторинг ресурсов, probes, историю, инциденты и объяснимую сетевую диагностику в `netweather.online`.

**Текущая линия:** `0.3.10-web`.

## Главное правило

Production NetWeather **не разворачивается** обычным `docker compose up` из рабочего дерева.

Production runtime изолирован от остальных сервисов VPS, а образ:
1. проверяется CI;
2. собирается на GitHub runner;
3. передаётся по forced-command SSH;
4. запускается root-owned helper с фиксированным security profile.

См. [DEPLOYMENT.md](DEPLOYMENT.md) и [../SECURITY.md](../SECURITY.md).

## Компоненты

```text
web/
├── backend/
│   ├── app/                FastAPI / scheduler / monitoring / DB
│   └── tests/              API, frontend and security contracts
├── frontend/
│   ├── index.html
│   └── assets/
│       ├── dashboard.js
│       └── dashboard.css
├── deploy/
│   ├── keenetic/           Domestic Probe
│   ├── security/           host-enforced production boundary
│   └── smoke-test.sh
├── Dockerfile
├── docker-compose.yml      local/dev hardened profile
└── DEPLOYMENT.md
```

## Probe model

### GLOBAL

Внешний VPS отвечает на вопросы:
- разрешается ли DNS;
- устанавливается ли TCP;
- проходит ли TLS;
- отвечает ли HTTP;
- как выглядит внешний traceroute.

### DOMESTIC

Российский probe нужен для сравнения с внешним контуром.

```text
GLOBAL OK + DOMESTIC FAIL
→ вероятна региональная / ISP-path проблема

GLOBAL FAIL + DOMESTIC FAIL
→ вероятнее проблема ресурса / общей сети

GLOBAL FAIL + DOMESTIC OK
→ проблема внешнего пути или VPS
```

### USER / BROWSER / DEVICE

Следующий контур — измерения из фактической сети пользователя. Browser Probe даст базовую диагностику без установки, Native/Router Probe — глубокую.

## Resource model

- группы — first-class;
- каталог содержит канонические ресурсы;
- каталоговые ресурсы не дублируются между группами;
- ручной URL, совпавший с каталогом, использует каталоговую identity;
- custom target остаётся пользовательским.

## UI contract

Источник правил: [../docs/UI_GUIDELINES.md](../docs/UI_GUIDELINES.md).

Основные требования:
- минимум 10 px для текста;
- capability-aware panels;
- единое поведение dialog;
- keyboard navigation;
- busy/disabled/error states;
- без dead controls;
- Overview без лишнего пустого пространства.

Глобальный поиск раскрывается как непрозрачный popup поверх dashboard: появление результатов не меняет высоту topbar и не сдвигает страницу. Если введённого HTTP/HTTPS-ресурса ещё нет, любой посетитель может добавить его как базовую проверку; изменение, удаление, ручные проверки, traceroute и расширенные probe-возможности остаются защищёнными.

## Local development

Для локальной разработки `docker-compose.yml` повторяет ключевые ограничения production:

- non-root;
- read-only rootfs;
- drop capabilities;
- no-new-privileges;
- dedicated data volume.

Перед локальным compose должна существовать внешняя сеть/volume, либо используйте эквивалентную dev-конфигурацию.

## Checks

```bash
python -m py_compile backend/app/*.py
node --check frontend/assets/dashboard.js
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
bash -n deploy/smoke-test.sh
```

CI дополнительно реально собирает hardened image и запускает его с production-like ограничениями.

## Production deployment

Workflow:

```text
.github/workflows/deploy-web.yml
```

Путь:

```text
commit
  ↓
Verify web
  ↓
Build isolated image on GitHub
  ↓
non-root assertion
  ↓
immutable image artifact
  ↓
forced-command SSH
  ↓
root-owned deploy helper
  ↓
health + security assertions
```

Обычные изменения `web/**` деплоятся автоматически, когда repository variable:

```text
NETWEATHER_DEPLOY_ENABLED=true
```

Maintenance-коммит, который **не должен** попасть в production:

```text
[no-deploy]
```

## Production security profile

Container:
- `10001:10001`;
- read-only root filesystem;
- `CAP_DROP=ALL`;
- `no-new-privileges`;
- no privileged mode;
- no Docker socket;
- no host bind mounts;
- only `/data` writable;
- resource limits.

Network:
- NetWeather may reach public Internet targets;
- NetWeather cannot initiate connections to VPS host;
- RFC1918 / CGNAT / link-local / VPN networks are blocked by `netweather_guard`.

## Secrets

Production env is host-owned:

```text
/etc/netweather/netweather.env
root:root 600
```

Do not put production secrets back into `/opt/NetWeather/web/.env`.

## Keenetic Domestic Probe

Agent:

```text
deploy/keenetic/netweather-probe.sh
```

It must use the **direct ISP path**, not HRNeo/AWG/VLESS bypass. Otherwise NetWeather measures the repaired route instead of the actual domestic network condition.

The probe:
- fetches current targets;
- reports DNS/TCP/TLS/HTTP timings;
- sends heartbeat/results;
- receives domestic traceroute tasks.

В комплект также входят воспроизводимый установщик и Entware-сервис:

```text
deploy/keenetic/install-netweather-probe.sh
deploy/keenetic/S99netweather-probe
```

Для рабочего роутера прямой ISP-интерфейс зафиксирован как `eth2.4`; агент не стартует без явного `NETWEATHER_DIRECT_INTERFACE` и не должен использовать `opkgtun0`/HRNeo. Подробная процедура и критерии приёмки находятся в [DEPLOYMENT.md](DEPLOYMENT.md).
