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

Last deployment-channel verification trigger: 2026-09-18.
