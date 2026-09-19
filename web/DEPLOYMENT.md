# NetWeather Web Deployment

Production web deployment is performed by the guarded GitHub Actions pipeline.

Security boundary:
- image is built off-host on GitHub Actions;
- VPS deploy key is forced-command only;
- production container runs as UID/GID 10001;
- root filesystem is read-only;
- all Linux capabilities are dropped;
- no-new-privileges is enforced;
- only the NetWeather data volume is writable;
- NetWeather has no Docker socket or host bind mounts;
- outbound access to the VPS host, private networks and VPN ranges is blocked by the dedicated nftables guard.
- production is public read-only; every mutation requires an owner session or API token;
- the application fails startup when no owner secret is configured.

Last deployment-channel verification trigger: 2026-09-19.


## 0.3.10 production verification

This marker intentionally triggers the guarded production pipeline after:
- interaction-contract CI passed;
- host isolation was verified;
- forced-command SSH was verified;
- deploy helper private-state temporary paths were installed on the VPS.
- runtime identity and Docker health were verified against the exact commit image.

Expected public health after deployment: `0.3.10-web`.
