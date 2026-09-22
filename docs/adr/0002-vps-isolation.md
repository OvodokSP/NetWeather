# ADR-0002: NetWeather is isolated from co-hosted VPS services

**Status:** Accepted

## Context

NetWeather shares the current VPS with unrelated services, including VPN infrastructure. A public web compromise must not imply access to those services.

## Decision

Production NetWeather uses a host-enforced isolation boundary:

- dedicated non-root UID/GID;
- read-only rootfs;
- no Linux capabilities;
- no-new-privileges;
- only dedicated data volume writable;
- no host bind mounts;
- no Docker socket;
- separate Docker network;
- nftables egress guard blocks host/private/VPN networks;
- off-host image build;
- forced-command deploy key;
- root-owned deployment helper.

## Consequences

- production compose/repository content does not control host mounts or privileges;
- deploy-user cannot use Docker directly;
- monitoring public resources remains possible;
- deep protection against a kernel/container-runtime escape still requires a separate VM/VPS.
