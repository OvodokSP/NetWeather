# NetWeather Architecture

## Product model

NetWeather is hardware-free network observability. It works with only the hosted service:

- `GLOBAL` — mandatory NetWeather VPS baseline;
- external measurement providers — event-driven independent confirmation;
- `USER` — optional Android software probe using the current device connection.

No router, Keenetic, Entware, Raspberry Pi, home server, VPN or root access is required.

## One source of truth

FastAPI and SQLite own resource identity, groups, global checks, incidents, history and diagnostic jobs. Web reads this API. Android synchronizes the same resource IDs and adds local device measurements when a user authorizes that capability.

Historical `EXTERNAL` rows migrate to `GLOBAL`. Historical router `DOMESTIC` rows are retained as `LEGACY` for data preservation but never participate in current conclusions.

## Measurement and diagnostics

`MeasurementProvider` isolates external services. `GlobalpingProvider` is the first implementation. `QuotaManager` protects 30% of the hourly budget by default for manual checks and new outages.

Priority order: `P0 MANUAL`, `P1 NEW_DOWN`, `P2 DEGRADED`, `P3 RECHECK`, `P4 BACKGROUND`.

Healthy resources use only the inexpensive VPS baseline. Deep diagnostics are event-driven, deduplicated and cooldown-limited.

## Deterministic assessment

`IncidentAssessment` produces one of `OK`, `SERVICE_DOWN`, `DEGRADED`, `LOCAL_NETWORK`, `ISP_OUTAGE`, `DNS_FAILURE`, `ROUTING_FAILURE`, `REGIONAL_OUTAGE`, `POSSIBLE_FILTERING`, `UNKNOWN`.

Unavailable evidence is never replaced with a guess. Without Android the UI says that **Your Network is unavailable** while Global State remains useful.

## External intelligence

OONI, IODA and official service status feeds are planned as cached, event-driven `StatusProvider` inputs. They must never be polled per healthy resource or presented as active until configured and verified.

## Production isolation

The non-root, read-only container, dedicated data volume, forced-command deploy key and nftables egress policy remain unchanged. See [../SECURITY.md](../SECURITY.md).
