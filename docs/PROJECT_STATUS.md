# NetWeather Project Status

## Verified checkpoint — 2026-09-23

- Web release: `0.4.1-web`; production: [netweather.online](https://netweather.online).
- Repository: `OvodokSP/NetWeather`; PR #4 (`NetWeather 0.4.1`) is merged.
- The canonical backend is FastAPI + SQLite. Web and Android use the same resource catalog and API.
- The service does not require a router, Keenetic, Entware, a home server, or user hardware.
- Measurement scopes: `GLOBAL` (VPS), `RUSSIA` (public Globalping probes selected with `country=RU`), and optional `USER` (paired Android device).
- Globalping, OONI, and IODA are enabled in production. Globalping is used for incident/manual diagnostics and the bounded Russian contour; ordinary healthy VPS checks do not consume its quota.
- Free basic resource monitoring and addition are enabled. Billing and paid deep-check entitlements remain disabled.
- Android preview `0.4.1-alpha` supports one-time-code pairing and sends local measurements only after the owner approves pairing. Current preview artifacts are debug-signed.

## Production snapshot

At the audit on 2026-09-23, `/api/health`, `/api/system`, `/api/diagnostics/status`, `/api/dashboard`, `/api/incidents`, `/api/resources`, `/api/groups`, and `/api/capabilities` returned HTTP 200. Health reported `0.4.1-web`; system reported 15 resources, 83,822 checks, Globalping/OONI/IODA enabled, and the scheduler/database healthy. Dashboard had a live `GLOBAL` probe and a live `RUSSIA` probe. Some Russian resource results were `UNKNOWN`; those are insufficient evidence to label a resource blocked.

One open incident was an acknowledged TLS expiry warning for Instagram. Acknowledged means read; it remains in the active list until the condition clears. The UI separates unread count from open incident count.

The deployed HTML, JavaScript, and CSS matched the repository's `main` branch at the audit point. `/` returned HTTP 200 for GET. `HEAD /` returned 405 with `Allow: GET`, which is expected for this GET-only route and is not a page failure.

## Confirmed product contracts

- A single backend owns resources, groups, checks, incidents, evidence, and device pairing.
- Global monitoring is useful without Android. Android is optional and is never treated as evidence for all of Russia.
- Russian availability is measured by public Globalping probes. Unknown provider results remain unknown.
- Deep diagnostics are event-driven, deduplicated, and quota-limited. Available paid capabilities stay hidden while billing is disabled.
- Production uses a non-root container, read-only root filesystem, dropped capabilities, restricted SSH delivery, an isolated data volume, and host-owned egress controls.
- Public users can read the dashboard and add basic HTTP/HTTPS resources. Owner-only actions require the owner session.
- Incident acknowledgement marks an event as read; it does not resolve or close an active condition.

## Remaining work

1. Capture and retain successful live-provider fixtures for Globalping, OONI, and IODA; provider availability is currently confirmed, but fixture-backed production response verification is still open.
2. Test pairing, sync, notifications, and responsive layout on physical Android devices, including a narrow screen.
3. Rehearse SQLite backup and restore on a production-like copy.
4. Configure Android production signing and publish a production-signed release.
5. Finish contextual help and remaining empty/error-state polish after device QA.
6. Decide whether selected manual deep diagnostics should become available before billing is introduced; do not consume external quota for healthy background checks.

## Recently corrected in this audit

- Removed obsolete Keenetic/Entware probe installers, service files, and their security-contract test.
- Removed the dead Agent API panel that advertised routes no longer served by the backend.
- Updated the README and cache-busted both web assets after the UI cleanup.
