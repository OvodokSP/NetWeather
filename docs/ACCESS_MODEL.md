# NetWeather access model

NetWeather has exactly three user levels. Authentication is separated from
the monitoring data plane: public status remains readable, while every
privileged operation is evaluated against an explicit entitlement.

| Level | How it is identified | Available | Limits |
|---|---|---|---|
| Guest | No account/session | Read dashboard, resource details, incidents, public history; add basic HTTP/HTTPS resource; pair a device only through an explicit short-lived code flow | Maximum 3 self-added resources per hour per IP; no editing/deletion; no manual checks, traceroute, probe management, exports or paid diagnostics |
| Subscriber | Account session with an active subscription entitlement | Everything in Guest plus owned-resource management, device sync, local-network results, alerts, history/export and paid diagnostic actions included in the plan | Default plan: 50 owned resources, 5 devices, 20 manual diagnostics/day, 10 traceroutes/day and 100 Globalping probe credits/day. Unused quota is not carried over. |
| Owner | Private owner session or server API token | Full administration, subscription/entitlement management, catalog and groups, all diagnostics, device revocation, audit and deployment controls | No product quota; operational provider/network safety limits still apply. |

## Enforcement rules

- Guest access is anonymous and read-only except for the intentionally public
  basic-resource-add operation.
- A device pairing code is not an access level. It is a short-lived grant used
  to attach one Android installation to an authenticated subscriber or owner.
  It is single-use, rate-limited, revocable and tied to a unique installation ID.
- API bearer tokens are never accepted as a substitute for a subscriber
  entitlement. The owner API token is only for owner automation.
- Web and Android must consume one capability response containing the effective
  role and remaining quotas.
- Provider quotas and safety limits remain active for the owner; “unlimited”
  means no product entitlement quota, not unlimited external-provider usage.

## Migration

Existing owner-password/API-token protection and the legacy domestic-probe agent
token remain valid during migration. Anonymous read/basic-add behavior stays
available. Subscriber accounts become active only after an entitlement store and
billing source are configured.
