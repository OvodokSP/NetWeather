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

The runtime keeps three independent evidence scopes: `GLOBAL` (VPS baseline), `RUSSIA` (public Globalping probes selected in Russia), and `USER` (Android local measurements). `RUSSIA` is never inferred from Android and `USER` is never presented as regional evidence.

## Measurement and diagnostics

`MeasurementProvider` isolates external services. `GlobalpingProvider` submits HTTP measurements, polls the documented result endpoint and normalizes per-probe results. `PersistentQuotaManager` stores usage in SQLite and protects 30% of the hourly budget by default for manual checks and new outages.

Priority order: `P0 MANUAL`, `P1 NEW_DOWN`, `P2 DEGRADED`, `P3 RECHECK`, `P4 BACKGROUND`.

Healthy resources use only the inexpensive VPS baseline. Deep diagnostics are event-driven, deduplicated and cooldown-limited.

## Deterministic assessment

`IncidentAssessment` produces one of `OK`, `SERVICE_DOWN`, `DEGRADED`, `LOCAL_NETWORK`, `ISP_OUTAGE`, `DNS_FAILURE`, `ROUTING_FAILURE`, `REGIONAL_OUTAGE`, `POSSIBLE_FILTERING`, `UNKNOWN`.

Unavailable evidence is never replaced with a guess. Without Android the UI says that **Your Network is unavailable** while Global State remains useful.

## Device authorization

Android starts an authorization session and shows a unique eight-character code. The owner enters that code on the Web settings page. The app polls with a separate high-entropy secret and receives a device bearer token once; only its HMAC digest is stored. A new attempt supersedes the previous pending code. Tokens are scoped to client-probe endpoints, expire, and can be revoked by the owner.

## External intelligence

OONI aggregation and IODA country alerts are cached, event-driven evidence inputs. A `StatusProvider` abstraction also reads public Statuspage summary feeds for the allowlisted GitHub and Cloudflare services. These feeds run only on an incident or owner-requested diagnosis, are cached in SQLite, and remain contextual evidence; they never override probe results or assert that a target is down. The adapter reads only the public `summary.json` endpoints, not authenticated management APIs. The public endpoint format is verified against [GitHub Status](https://www.githubstatus.com/api/v2/summary.json) and [Cloudflare Status](https://www.cloudflarestatus.com/api/v2/summary.json); the Statuspage API documentation describes the separately authenticated management API at [developer.statuspage.io](https://developer.statuspage.io/).

Provider, diagnostic, incident, and global/local state transitions are returned in each resource detail's evidence timeline. The API retains and returns up to the most recent 12 months for this view; detailed check samples continue to use their own shorter retention policy. Raw provider payloads and credentials are excluded from the timeline.

`GET /api/capabilities` publishes the free, owner-only, and not-yet-enabled paid capability contract. Basic resource addition and global monitoring are free. Paid deep-check entitlements and billing are currently disabled; this endpoint does not claim that a payment or account system exists.

## Production isolation

The non-root, read-only container, dedicated data volume, forced-command deploy key and nftables egress policy remain unchanged. See [../SECURITY.md](../SECURITY.md).
