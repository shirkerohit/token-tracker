"""Together AI adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

USAGE_URL = "https://api.together.xyz/v1/usage"


def fetch_together(api_key: str) -> UsageRecord:
    """Fetch usage from Together AI.

    Returns usage in USD.
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(USAGE_URL, headers=headers)
        if resp.status_code != 200:
            return make_error_record(
                "together", f"usage: HTTP {resp.status_code}"
            )

        data = resp.json()
        # Together: {"usage": {"total_usage": 123.45, "currency": "USD"}}
        usage = data.get("usage", {})
        used = usage.get("total_usage", 0)
        currency = usage.get("currency", "USD")

    return UsageRecord(
        provider="together",
        used=used,
        unit=currency,
    )