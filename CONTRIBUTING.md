# Contributing to NetWeather

NetWeather находится в активной разработке. Изменения должны сохранять общую модель продукта: единый интерфейс, probes как источники наблюдения и объяснимый fault-domain.

## Ветки

- `main` — стабильная линия.
- feature-ветки — разработка.
- крупные изменения идут через pull request.

Текущий web-контур развивается в `feature/web-vps-monitoring`.

## Перед PR

### Web

```bash
python -m py_compile web/backend/app/*.py
node --check web/frontend/assets/dashboard.js
PYTHONPATH=web/backend python -m unittest discover -s web/backend/tests -v
```

### Android

```bash
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

## UI contract

Любое изменение web UI должно соблюдать [docs/UI_GUIDELINES.md](docs/UI_GUIDELINES.md).

Минимум:

- никакого текста меньше 10 px;
- кнопка не выглядит активной, если действие недоступно;
- async action имеет busy-state и защищён от double-submit;
- modal закрывается единообразно;
- destructive action требует подтверждения;
- focus state видим;
- недоступная capability не оставляет пустую/мёртвую панель;
- группы ресурсов сохраняются во всех flows.

## Security

Не добавляйте:

- Docker socket mounts;
- privileged containers;
- host bind mount в production NetWeather;
- membership deploy-user в `docker`;
- wildcard CORS;
- private-target access в production.

Security contract должен оставаться зелёным.

## Коммиты

Рекомендуемый стиль:

```text
feat(web): ...
fix(web): ...
fix(deploy): ...
security(web): ...
test(web): ...
docs: ...
```

Maintenance commit, который затрагивает `web/**`, но **не должен** попадать в production, помечается:

```text
[no-deploy]
```

## Definition of Done

Изменение считается готовым, когда:

1. поведение реализовано;
2. UI-state предусмотрены;
3. regression test добавлен там, где это возможно;
4. CI зелёный;
5. документация обновлена, если изменился контракт;
6. production deploy не ослабляет isolation boundary.
