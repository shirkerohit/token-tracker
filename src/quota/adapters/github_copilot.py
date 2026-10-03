"""GitHub Copilot adapter (internal endpoint used by VS Code)."""

import httpx

from quota.records import UsageRecord, make_error_record

COPILOT_INTERNAL_URL = "https://api.github.com/copilot_internal/user"


def fetch_github_copilot(token: str) -> list[UsageRecord]:
    """Fetch Copilot quota from internal endpoint.

    Returns separate records for chat, completions, and premium_interactions.
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/json",
        "Editor-Version": "vscode/1.96.2",
        "User-Agent": "GitHubCopilotChat/0.26.7",
        "X-GitHub-Api-Version": "2025-04-01",
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(COPILOT_INTERNAL_URL, headers=headers)
        if resp.status_code == 401:
            return [make_error_record("github_copilot", "Invalid token (401)")]
        if resp.status_code == 403:
            return [make_error_record("github_copilot", "Token lacks Copilot access (403)")]
        if resp.status_code == 404:
            return [make_error_record("github_copilot", "Copilot not enabled on this account (404)")]
        if resp.status_code != 200:
            return [make_error_record("github_copilot", f"copilot_internal: HTTP {resp.status_code}")]

        data = resp.json()

        def get_first(d, *keys):
            for k in keys:
                v = d.get(k)
                if v is not None:
                    return v
            return None

        def find_key(d, target_keys, max_depth=3):
            if max_depth <= 0:
                return None
            if not isinstance(d, dict):
                return None
            for k in target_keys:
                if k in d and d[k] is not None:
                    return d[k]
            for v in d.values():
                if isinstance(v, dict):
                    result = find_key(v, target_keys, max_depth - 1)
                    if result is not None:
                        return result
            return None

        snapshots = data.get("quota_snapshots", {})

        # Get reset date
        reset_date_str = get_first(data, "reset", "quota_reset_date", "quota_reset_date_utc", "resetAt", "quotaResetDate")
        if reset_date_str is None:
            reset_date_str = find_key(data, ["reset", "quota_reset_date", "quota_reset_date_utc", "resetAt", "quotaResetDate"])

        reset_at = None
        if reset_date_str:
            from datetime import datetime
            reset_at = datetime.fromisoformat(reset_date_str.replace("Z", "+00:00"))

        records = []

        # Process each bucket: chat, completions, premium_interactions
        for bucket_name in ("chat", "completions", "premium_interactions"):
            bucket = snapshots.get(bucket_name, {})
            if not bucket:
                continue

            entitlement = bucket.get("entitlement")
            credits_used = bucket.get("credits_used")
            remaining = bucket.get("remaining")
            percent_remaining = bucket.get("percent_remaining")

            # Skip if no entitlement (unlimited or not applicable)
            if entitlement is None or entitlement == 0:
                # Still show if it has usage data
                if credits_used is not None and credits_used > 0:
                    pass
                else:
                    continue

            used = credits_used
            limit = entitlement
            unit = "credits"

            # For premium_interactions legacy, use remaining/percent
            if bucket_name == "premium_interactions":
                if credits_used is None or credits_used == 0:
                    # Legacy mode: use remaining/percent
                    remaining = bucket.get("remaining")
                    percent_remaining = bucket.get("percent_remaining")
                    entitlement = bucket.get("entitlement")
                    if entitlement is not None and remaining is not None:
                        used = entitlement - remaining
                    elif entitlement is not None and percent_remaining is not None:
                        used = entitlement * (100 - percent_remaining) / 100
                    else:
                        used = None
                    limit = entitlement
                    unit = "requests"
                else:
                    used = credits_used
                    limit = entitlement
                    unit = "credits"
            else:
                # chat and completions use credits_used
                used = credits_used
                limit = entitlement
                unit = "credits"

            records.append(UsageRecord(
                provider=f"github_copilot_{bucket_name}",
                used=used,
                unit=unit,
                reset_at=reset_at,
                provider_limit=limit,
            ))

        # Get reset date
        reset_at = None
        def get_first(d, *keys):
            for k in keys:
                v = d.get(k)
                if v is not None:
                    return v
            return None

        def find_key(d, target_keys, max_depth=3):
            if max_depth <= 0:
                return None
            if not isinstance(d, dict):
                return None
            for k in target_keys:
                if k in d and d[k] is not None:
                    return d[k]
            for v in d.values():
                if isinstance(v, dict):
                    result = find_key(v, target_keys, max_depth - 1)
                    if result is not None:
                        return result
            return None

        reset_date_str = get_first(data, "reset", "quota_reset_date", "quota_reset_date_utc", "resetAt", "quotaResetDate")
        if reset_date_str is None:
            reset_date_str = find_key(data, ["reset", "quota_reset_date", "quota_reset_date_utc", "resetAt", "quotaResetDate"])

        if reset_at is None and reset_date_str:
            from datetime import datetime
            reset_at = datetime.fromisoformat(reset_date_str.replace("Z", "+00:00"))

        # Update reset_at on all records
        for r in records:
            r.reset_at = reset_at

        return records