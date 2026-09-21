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
- [ ] authenticated per-user upload of Android `USER` measurements
- [ ] process-safe persisted quota accounting and result polling
- [ ] event-triggered OONI/IODA/status-page cache
- [ ] physical-device Android and responsive Web matrix

## 0.5 — Evidence and accounts

- [ ] user accounts and device enrollment
- [ ] `StatusProvider` abstraction
- [ ] OONI/IODA cached evidence
- [ ] multi-region Globalping result normalization
- [ ] explainable evidence timeline and confidence
- [ ] free/paid capability registry; basic resource addition remains public

## 1.0 — Stable service

- reproducible hardened deployment and rollback;
- one backend/API/data model for Web and Android;
- no required user hardware;
- useful global monitoring without the Android app;
- honest unavailable/stale/error states;
- production-signed Android release;
- backup/restore, regression and representative-device QA.
