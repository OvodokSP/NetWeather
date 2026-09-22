from __future__ import annotations


def capability_registry(*, owner: bool, globalping_enabled: bool) -> dict:
    """Describe product access without pretending payment/account entitlements exist."""
    return {
        "version": 1,
        "billing_enabled": False,
        "plans": {
            "free": {
                "available": True,
                "capabilities": [
                    "dashboard.read",
                    "resource.add_basic",
                    "resource_catalog.read",
                    "monitor.global",
                    "incident_history.read",
                    "probe.android_local",
                ],
            },
            "paid": {
                "available": False,
                "capabilities": ["diagnostics.deep_manual", "diagnostics.traceroute"],
                "reason": "Платные проверки пока не подключены",
            },
        },
        "service": {
            "globalping_incident_confirmation": globalping_enabled,
            "globalping_healthy_background_checks": False,
        },
        "owner_controls": {
            "authenticated": owner,
            "capabilities": ["resource.manage", "device.manage", "diagnostics.admin"] if owner else [],
        },
    }
