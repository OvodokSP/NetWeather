# Security Policy

## Модель угроз

Production NetWeather рассматривается как потенциально компрометируемый публичный web-сервис. Компрометация приложения **не должна автоматически давать доступ к остальным сервисам VPS**.

Это defence-in-depth граница на одном Linux VPS. Она существенно уменьшает blast radius, но не является математической гарантией против неизвестной уязвимости Linux kernel / container runtime. Для максимально сильной границы production NetWeather следует переносить в отдельную VM/VPS.

## Текущая production-граница

NetWeather запускается:

- как `UID:GID 10001:10001`;
- с read-only root filesystem;
- с `CAP_DROP=ALL`;
- с `no-new-privileges`;
- без privileged mode;
- без Docker socket;
- без host bind mounts;
- с единственным writable Docker volume `/data`;
- с лимитами CPU, RAM, PID и файловых дескрипторов;
- в отдельной Docker-сети `netweather-isolated`.

Отдельная nftables-таблица `netweather_guard` запрещает исходящие соединения NetWeather к:

- самому VPS;
- RFC1918;
- CGNAT;
- link-local / metadata;
- VPN-подсетям;
- другим приватным Docker-сетям.

Публичный интернет остаётся доступным для мониторинга.

## Deployment

Production image:

1. проверяется CI;
2. собирается **вне VPS** на GitHub runner;
3. проверяется как non-root image;
4. передаётся на VPS как image archive;
5. принимается отдельным SSH key;
6. key принудительно связан с `netweather-ssh-gate`;
7. произвольный shell / `id` / `bash` этим key запрещены;
8. root-owned helper запускает только зафиксированный hardened runtime;
9. health/security assertions выполняются после запуска.

Deploy user не состоит в группе `docker`.

## VPN regression boundary

NetWeather production deployment must preserve unrelated VPN services on the shared VPS. The root-owned `/usr/local/sbin/netweather-vpn-invariants` checker reads only host-owned expectations from `/etc/netweather/vpn-invariants.env` and runs before and after every NetWeather runtime replacement.

A failed pre-check aborts without changing the NetWeather container. A failed post-check triggers NetWeather rollback to the previous hardened image and fails the deploy. The checker covers nginx syntax, VLESS/Xray runtime + TLS identity, NetWeather-domain TLS isolation, and the configured AWG runtime/UDP redirect.

## SSRF

Production принудительно использует:

```text
ALLOW_PRIVATE_TARGETS=false
```

Даже если значение появится в repository-controlled config, deployment helper переопределяет его в `false`.

## Secrets

Production secrets находятся вне рабочего дерева NetWeather:

```text
/etc/netweather/netweather.env
```

Ожидаемые права:

```text
root:root 600
```

Секреты не должны коммититься в Git.

## Web security baseline

- wildcard CORS не используется;
- SPA file serving ограничен frontend root;
- production разрешает без входа только чтение и базовое добавление ресурса в общий GLOBAL-мониторинг;
- публичное добавление custom-target ограничено по частоте и всегда использует безопасный фиксированный профиль без alerts;
- изменение/удаление ресурсов, ручные проверки, группы, инциденты и служебные write API требуют owner-session или API token;
- отсутствие owner secret останавливает запуск production-контейнера;
- пользовательский target проходит private-target protection;
- browser-facing ошибки не должны раскрывать секреты или host paths.

## Reporting

Не публикуйте секреты, приватные ключи, deployment credentials или рабочие exploit details в публичном issue.

Для security issue используйте приватный канал владельца репозитория / GitHub Security Advisory.

## Проверка

Security contract автоматически проверяется в:

```text
web/backend/tests/test_security_contract.py
.github/workflows/web-checks.yml
```

Любое ослабление ключевых ограничений должно намеренно менять security test, а не обходить его.
