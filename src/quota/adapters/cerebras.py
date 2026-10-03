"""Cerebras adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

USAGE_URL = "https://api.cerebras.ai/v1/usage"


def fetch_cerebras(api_key: str) -> UsageRecord:
    """Fetch usage from Cerebras.

    Returns usage in USD.
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(USAGE_URL, headers=headers)
        if resp.status_code != 200:
            return make_error_record(
                "cerebras", f"usage: HTTP {resp.status_code}"
            )

        data = resp.json()
        used = data.get("total_usage", 0)
        currency = data.get("currency", "USD")

    return UsageRecord(
        provider="cerebras",
        used=used,
        unit=currency,
    )