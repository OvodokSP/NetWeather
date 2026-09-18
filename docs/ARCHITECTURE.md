# NetWeather Architecture

## Product model

NetWeather is a multi-probe network observability product. The backend does not treat one probe as “truth”; it compares independent vantage points and turns their measurements into an explainable conclusion.

## Probe scopes

### GLOBAL
External VPS outside the user network.

Typical checks:
- DNS
- TCP
- TLS
- HTTP
- response time
- traceroute

### DOMESTIC
A probe inside the target regional/network contour, currently designed around Keenetic/router deployment.

Purpose:
- distinguish global outage from regional/operator path problems;
- provide traceroute from a domestic vantage point.

### USER / BROWSER / DEVICE
A probe that represents the user’s actual connection.

Browser Probe provides installation-free reachability and baseline measurements. Native probes extend this with deeper network access.

## Data flow

```text
resource
   │
   ├── GLOBAL probe
   ├── DOMESTIC probe
   └── USER probe
          │
          ▼
 normalized measurements
          │
          ▼
 comparison / fault-domain engine
          │
          ▼
 dashboard + incidents + history
```

## Fault-domain principle

A raw error such as `TLS_ERROR` is not an answer by itself.

NetWeather should explain the failure using evidence:

```text
GLOBAL OK + DOMESTIC FAIL
→ likely regional/operator path issue

GLOBAL FAIL + DOMESTIC FAIL
→ likely resource/global-path outage

GLOBAL OK + USER FAIL + USER→NetWeather OK
→ likely user ISP / local route restriction
```

The engine must keep evidence and confidence separate from the human-readable conclusion.

## Web architecture

```text
FastAPI
├── resources/groups
├── monitoring scheduler
├── probes
├── incidents/events
├── history/realtime
├── traceroute
└── frontend SPA

SQLite
├── resources
├── groups
├── checks
├── probes
├── incidents
└── preferences/state
```

## Resource identity

Catalog resources have a persistent `catalog_key`.

Rules:
- one catalog service → one canonical identity;
- catalog items do not duplicate across groups;
- manual input that matches a catalog service resolves to the catalog identity;
- custom targets remain custom.

## UI capabilities

UI must not render dead functionality.

A panel is visible only when:
1. the capability is available;
2. the user has not hidden it;
3. there is meaningful data for it where applicable.

This same contract will later support licensing without rebuilding the interface.

## Production isolation

See [../SECURITY.md](../SECURITY.md).

NetWeather is deliberately isolated from the rest of the VPS. Production code cannot choose Docker mounts, privileges or networking policy; those are enforced by root-owned host helpers.
