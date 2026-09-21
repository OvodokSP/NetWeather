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
- production is publicly readable and permits anonymous addition of a basic HTTP/HTTPS resource;
- editing, deletion, manual checks, traceroute, administration and paid probe types require an owner session or API token;
- the application fails startup when no owner secret is configured.

Last deployment-channel verification trigger: 2026-09-19.


## Mandatory VPN invariants

NetWeather shares the VPS with independent VPN services. A NetWeather deployment is not successful unless those services remain healthy.

Production uses the root-owned checker:

```text
/usr/local/sbin/netweather-vpn-invariants
/etc/netweather/vpn-invariants.env
```

The host-owned config defines the expected public IP/domain, Xray container/backend port and AWG container/interface/UDP redirect. The deploy payload cannot choose these values.

Deployment contract:

1. run VPN invariants before removing the old NetWeather container;
2. if pre-check fails, abort without changing NetWeather;
3. deploy and verify the new NetWeather image;
4. run the same VPN invariants again;
5. if post-check fails, automatically roll NetWeather back to the previous hardened image and fail the deploy;
6. verify the VPN invariants again after rollback and surface any remaining host-level failure.

The checker verifies nginx syntax, the VLESS/Xray runtime and loopback backend, TLS identity for the VPN public IP, independent TLS identity for the NetWeather domain, the AWG container/interface/backend UDP listener, and (when configured) the UDP public-port redirect used by HomeRoute.

## 0.4.1 production verification

This marker intentionally triggers the guarded production pipeline after:
- interaction-contract CI passed;
- host isolation was verified;
- forced-command SSH was verified;
- deploy helper private-state temporary paths were installed on the VPS.
- runtime identity and Docker health were verified against the exact commit image.

Expected public health after deployment: `0.4.1-web`.

The release has no router-side installation step. Optional external diagnostics are enabled only with `NETWEATHER_GLOBALPING_ENABLED=true`; without it `/api/diagnostics/status` must report `enabled: false` and the baseline service remains fully operational.

## SQLite backup and restore

`python -m app.backup` uses SQLite's online backup API, checks the produced database with `PRAGMA integrity_check`, writes backups with mode `0600`, and atomically replaces the destination. The `restore` action requires `--offline-confirmed`, validates the source first, refuses a target with `-wal`/`-shm` sidecars, and saves a `.pre-restore-<timestamp>.sqlite` rollback copy beside an existing target.

Example for a disposable/local database:

```bash
PYTHONPATH=web/backend python -m app.backup backup \
  --source /path/to/netweather.db --destination /safe/backup/netweather.sqlite
PYTHONPATH=web/backend python -m app.backup restore \
  --source /safe/backup/netweather.sqlite --destination /path/to/netweather.db \
  --offline-confirmed
```

Do not run restore against a live production database. Production backup/restore still needs a supervised rehearsal through the approved maintenance channel; the deploy workflow does not execute database restoration and must preserve the `/data` volume during image replacement or rollback.
