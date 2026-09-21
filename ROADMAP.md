# NetWeather Roadmap

## 0.4 — Hardware-free convergence

- [x] VPS `GLOBAL` baseline and shared resource/group identity
- [x] remove Keenetic/Entware/router runtime, API and CI dependency
- [x] preserve former router history as excluded `LEGACY` telemetry
- [x] deterministic incident classification
- [x] `MeasurementProvider` and Globalping adapter
- [x] priority quota manager with configurable 30% reserve
- [x] diagnostic deduplication/cooldown foundation
- [x] explicit Global State / Your Network Web UX
- [x] Android pulls the shared resource catalog and global state
- [x] authenticated per-device upload of Android `USER` measurements via expiring one-time code
- [x] process-safe persisted quota accounting and Globalping result polling/classification
- [x] event-triggered cached OONI/IODA evidence adapters
- [x] official status feed adapter for supported GitHub and Cloudflare Statuspage services
- [x] per-resource evidence timeline with up to 12 months of history
- [ ] live-provider response smoke for Globalping, OONI and IODA from the deployed service
- [ ] physical-device Android and responsive Web matrix

## 0.5 — Evidence and accounts

- [x] owner-approved device enrollment and revocation
- [x] `StatusProvider` abstraction
- [x] OONI/IODA cached evidence foundation
- [x] multi-region Globalping HTTP result normalization
- [x] explainable evidence and confidence in the shared resource model
- [x] long-term evidence timeline and initial official-status providers
- [x] free/paid capability registry; basic resource addition remains public, paid plan remains disabled until billing exists

## 1.0 — Stable service

- [x] reproducible hardened deployment and rollback;
- [x] one backend/API/data model for Web and Android;
- [x] no required user hardware;
- [x] useful global monitoring without the Android app;
- [x] honest unavailable/stale/error states;
- [ ] production-signed Android release (signing material not configured);
- [ ] backup/restore rehearsal and physical-device QA.
