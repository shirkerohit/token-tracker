"""Perplexity adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

USAGE_URL = "https://api.perplexity.ai/v1/usage"


def fetch_perplexity(api_key: str) -> UsageRecord:
    """Fetch usage from Perplexity.

    Returns usage in USD.
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(USAGE_URL, headers=headers)
        if resp.status_code != 200:
            return make_error_record(
                "perplexity", f"usage: HTTP {resp.status_code}"
            )

        data = resp.json()
        used = data.get("total_usage", 0)
        currency = data.get("currency", "USD")

    return UsageRecord(
        provider="perplexity",
        used=used,
        unit=currency,
    )