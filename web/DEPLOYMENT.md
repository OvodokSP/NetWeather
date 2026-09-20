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


## 0.3.10 production verification

This marker intentionally triggers the guarded production pipeline after:
- interaction-contract CI passed;
- host isolation was verified;
- forced-command SSH was verified;
- deploy helper private-state temporary paths were installed on the VPS.
- runtime identity and Docker health were verified against the exact commit image.

Expected public health after deployment: `0.3.10-web`.

## Keenetic DOMESTIC probe

The router probe is installed independently from the VPS container. For this deployment its verified direct ISP path is:

```text
interface: eth2.4
address:   5.3.168.105/22
gateway:   5.3.171.254
```

It must not use `opkgtun0`, HRNeo, AmneziaWG or policy-routing table 301. The agent refuses to start without an explicit direct interface and applies it to every HTTP check, API request and traceroute.

Installation files:

```text
deploy/keenetic/install-netweather-probe.sh
deploy/keenetic/netweather-probe.sh
deploy/keenetic/S99netweather-probe
```

The installer requires an exact 40-character Git commit, downloads the agent and service from that immutable revision, verifies their embedded SHA-256 checksums, performs a one-cycle smoke test and starts the Entware service. It prompts for `NETWEATHER_AGENT_TOKEN`; do not put that token in shell history or issue output.

Runtime state:

```text
/opt/etc/netweather-probe.env       root-only configuration (0600)
/opt/var/run/netweather-probe.pid   supervised process
/opt/var/run/netweather-probe/last-success
/opt/var/log/netweather-probe.log
```

Verification on Keenetic:

```sh
/opt/etc/init.d/S99netweather-probe status
tail -n 50 /opt/var/log/netweather-probe.log
ip route get 5.3.171.254
```

`status` becomes degraded when no successful cycle has completed for more than 180 seconds. The final product verification is complete only after the public `/api/probes` response reports `RU_VORONEZH_HOME` online and a DOMESTIC traceroute task returns through `eth2.4`.
