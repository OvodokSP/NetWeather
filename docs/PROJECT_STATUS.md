# NetWeather Project Status

## Current checkpoint

**Web:** `0.4.1-web` candidate
**Development branch:** `feature/web-vps-monitoring`
**Production domain:** `netweather.online`

## Confirmed foundation

- Global VPS monitoring is working and is the hardware-free baseline.
- Keenetic/Entware/router runtime and agent API have been removed; old telemetry is retained as excluded `LEGACY` data.
- Deterministic assessment, provider abstraction and a quota reserve are implemented.
- Globalping submission, persistent quota accounting, result polling and conservative multi-probe classification are implemented.
- OONI and IODA evidence adapters are event-driven and cached; external failures do not alter the baseline conclusion.
- `StatusProvider` reads allowlisted GitHub and Cloudflare public status summaries only on incidents/manual diagnostics; it adds context without overriding probe results.
- Resource details expose a redacted evidence timeline from checks, incidents, and providers for up to 12 months.
- `GET /api/capabilities` declares free basic resource addition, owner-only controls, and paid checks disabled until billing/entitlements exist.
- Android device enrollment uses an expiring unique code approved by the owner on the Web site; device tokens are independently revocable.
- Resource groups are implemented.
- Ranked resource catalog is implemented.
- Manual/catalog duplicate protection is implemented.
- Incidents and history are implemented.
- Overview is configurable.
- Web typography has a tested 10 px minimum.
- Production container is non-root/read-only/capability-free.
- NetWeather cannot initiate connections to host/private/VPN networks.
- Deployment key is forced-command only.
- Production image build happens off-host.
- Production UI is publicly readable; anonymous users can add a basic HTTP/HTTPS resource, while privileged mutations require an owner session.
- Catalog anti-bot HTTP rejections are represented as reachable rather than false outages.
- Android latest results and interval settings use persisted reactive state.
- Android `0.4.1-alpha` uploads local measurements only after explicit device pairing. Its preview APK is published only after the updated CI/release workflow succeeds.

## Deployment channel

End-to-end auto-deploy is verified and active for the development branch.

Verified:
- repository variable enables workflow;
- web verification succeeds;
- production image builds off-host;
- non-root image assertion succeeds;
- artifact reaches VPS over restricted SSH.
- deploy helper uses root-owned state, verifies the exact image identity, and waits for Docker health;
- production starts in mandatory owner-auth mode and fails closed if no owner secret is configured.

## Current UI checkpoint

Completed in 0.3.10:
- shared dialog open/close/focus behavior;
- backdrop close and Escape contract;
- focus return to opener;
- explicit focus-visible states;
- busy-state / double-submit protection;
- custom destructive confirmation dialog;
- keyboard global search navigation;
- stale Core state;
- real map-region filter;
- live probe layer on the map page;
- GitHub project documentation/templates refresh.
- public basic-resource addition / protected privileged-mutation access model;
- non-shifting opaque search overlay with keyboard navigation;
- privacy-safe local resource icons without third-party browser requests;
- fault-domain panel hidden until an independent comparison probe exists.
- operational Overview with freshness, resource-count and median-latency KPIs;
- problem-first bounded resource table and explicit issue filter;
- readable natural page scrolling instead of viewport compression;
- catalog groups retain natural height and use one shared catalog scrollbar.

Next UI work:
- physical-device verification of Global State / Your Network on representative phones;
- contextual help/tooltips and remaining empty/error-state polish.

## Next functional work

1. Verify live Globalping, OONI and IODA responses from production and retain real response fixtures for contract regression.
2. Complete representative physical-device pairing and responsive-layout QA.
3. Perform an application data backup/restore rehearsal without touching other VPS services.
4. Configure a production signing key before creating a signed Android release; preview remains debug-signed.
5. Billing and paid entitlements remain disabled until the licensing model is selected.
