# NetWeather Agent Rules

These rules apply to automated coding agents and maintenance work.

## 1. Preserve the product model

NetWeather is a multi-probe network observability system.

Do not collapse:
- GLOBAL;
- DOMESTIC;
- USER / BROWSER / DEVICE

into one generic “availability” source.

The product goal is to explain **where a network failure starts**, not only whether one request failed.

## 2. Do not rewrite stable subsystems without a reason

Prefer small, reviewable changes over full rewrites.

Keep:
- existing database data;
- resource/group identity;
- deployment isolation;
- Android persisted state.

## 3. Web UI contract

Every web change follows `docs/UI_GUIDELINES.md`.

Hard rules:
- no rendered text below 10 px;
- no dead controls;
- async buttons must prevent double-submit;
- unavailable capabilities are hidden;
- dialogs share one behavior contract;
- groups are preserved in resource flows;
- loading/empty/error states are explicit.

## 4. Web security contract

Never add:
- `privileged: true`;
- Docker socket mounts;
- production host bind mounts;
- deploy-user membership in `docker`;
- wildcard CORS;
- production private-target monitoring.

Production runtime policy is host-owned. Repository code must not be able to choose arbitrary mounts/capabilities.

Security tests must remain green.

## 5. Deployment

- Production image is built off-host.
- Deploy key is forced-command only.
- Use `[no-deploy]` on maintenance commits under `web/**` that must not reach production.
- Do not touch nginx, AWG, Xray or unrelated VPS services from NetWeather deployment code.
- Rollback must preserve the NetWeather data volume.

## 6. Android

- Do not use Python scripts to patch Android code in CI.
- GitHub Actions builds through Gradle.
- Widgets, UI and WorkManager use the same persisted network state.
- Do not use `PeriodicWorkRequest` for intervals below 15 minutes.
- Keep Android as a Native Probe in the common NetWeather architecture.

## 7. Tests

Before considering a change complete:

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

## 8. Documentation

Update the relevant contract when behavior changes:
- `README.md`
- `ROADMAP.md`
- `SECURITY.md`
- `docs/ARCHITECTURE.md`
- `docs/UI_GUIDELINES.md`

Do not document planned behavior as already implemented.
