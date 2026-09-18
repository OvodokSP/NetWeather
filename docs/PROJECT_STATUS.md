# NetWeather Project Status

## Current checkpoint

**Web:** `0.3.10-web`  
**Development branch:** `feature/web-vps-monitoring`  
**Production domain:** `netweather.online`

## Confirmed foundation

- Global VPS monitoring is working.
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

## Deployment channel

End-to-end auto-deploy is being finalized.

Verified:
- repository variable enables workflow;
- web verification succeeds;
- production image builds off-host;
- non-root image assertion succeeds;
- artifact reaches VPS over restricted SSH.

Last remaining deployment corrective:
- deploy helper temporary files moved from shared `/tmp` to root-owned deployment state directory.

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

Next UI work:
- responsive pass on narrow layouts;
- contextual help/tooltips;
- remaining empty/error-state polish;
- browser-probe panels when capability exists.

## Next functional work

1. Keenetic Domestic Probe.
2. Browser Probe.
3. Unified probe comparison.
4. Explainable fault-domain.
5. Alerts/reporting refinement.
6. Accounts/capabilities/licensing only after the base tool is complete.
