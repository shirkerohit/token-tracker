"""OpenRouter adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

CREDITS_URL = "https://openrouter.ai/api/v1/credits"
KEY_URL = "https://openrouter.ai/api/v1/auth/key"


def fetch_openrouter(api_key: str) -> UsageRecord:
    """Fetch usage from OpenRouter.

    Returns used amount in USD (from credits) and rate limit info from key endpoint.
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=10.0) as client:
        # Get credits (spend)
        credits_resp = client.get(CREDITS_URL, headers=headers)
        if credits_resp.status_code != 200:
            return make_error_record(
                "openrouter", f"credits: HTTP {credits_resp.status_code}"
            )

        credits_data = credits_resp.json()
        # OpenRouter credits: {"data": {"total_credits": 50, "total_usage": 38.2}}
        # total_usage is in USD, total_credits is the hard cap
        credit_info = credits_data.get("data", {})
        used = credit_info.get("total_usage", 0)
        provider_limit = credit_info.get("total_credits")

        # Get rate limit info
        key_resp = client.get(KEY_URL, headers=headers)
        reset_at = None
        if key_resp.status_code == 200:
            key_data = key_resp.json()
            # key_data: {"data": {"limit": 100, "remaining": 85, "reset": 1234567890}}
            # reset is a unix timestamp
            reset_ts = key_data.get("data", {}).get("reset")
            if reset_ts:
                from datetime import datetime, timezone

                reset_at = datetime.fromtimestamp(reset_ts, tz=timezone.utc)

    return UsageRecord(
        provider="openrouter",
        used=used,
        unit="USD",
        reset_at=reset_at,
        provider_limit=provider_limit,
    )