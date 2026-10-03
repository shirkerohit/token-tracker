"""GitHub adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

RATE_LIMIT_URL = "https://api.github.com/rate_limit"


def fetch_github(token: str) -> UsageRecord:
    """Fetch rate limit from GitHub.

    Returns used requests (limit - remaining) in requests unit.
    """
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(RATE_LIMIT_URL, headers=headers)
        if resp.status_code != 200:
            return make_error_record(
                "github", f"rate_limit: HTTP {resp.status_code}"
            )

        data = resp.json()
        # GitHub rate limit: {"resources": {"core": {"limit": 5000, "remaining": 4999, "reset": 1234567890}}}
        core = data.get("resources", {}).get("core", {})
        limit = core.get("limit", 5000)
        remaining = core.get("remaining", 0)
        used = limit - remaining
        reset_ts = core.get("reset")

        reset_at = None
        if reset_ts:
            from datetime import datetime, timezone

            reset_at = datetime.fromtimestamp(reset_ts, tz=timezone.utc)

    return UsageRecord(
        provider="github",
        used=used,
        unit="requests",
        reset_at=reset_at,
        provider_limit=limit,
    )