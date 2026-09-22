# ADR-0001: Multi-probe comparison is the core product model

**Status:** Accepted

## Context

A single monitoring location cannot distinguish:
- service outage;
- regional restriction;
- ISP path problem;
- local/user-network problem.

## Decision

NetWeather models observations by probe scope and compares them.

Primary scopes:
- GLOBAL;
- USER/ANDROID DEVICE.

A diagnosis must retain the measurements/evidence that produced it.

## Consequences

- resource state is not derived from one request;
- UI may show different results per contour;
- fault-domain work builds on normalized probe data;
- Android is an optional software probe; no user-owned router or server is required.
