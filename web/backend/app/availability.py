REACHABLE_STATUSES = frozenset({"OK", "HTTP_REJECTED"})


def is_reachable(status: str | None) -> bool:
    """A completed HTTP exchange proves reachability even when a curated site rejects the probe."""
    return status in REACHABLE_STATUSES
