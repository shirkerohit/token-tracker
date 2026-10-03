"""Mistral adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

USAGE_URL = "https://api.mistral.ai/v1/usage"


def fetch_mistral(api_key: str) -> UsageRecord:
    """Fetch usage from Mistral.

    Returns usage in EUR (Mistral bills in EUR).
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(USAGE_URL, headers=headers)
        if resp.status_code != 200:
            return make_error_record(
                "mistral", f"usage: HTTP {resp.status_code}"
            )

        data = resp.json()
        used = data.get("total_usage", 0)
        currency = data.get("currency", "EUR")

    return UsageRecord(
        provider="mistral",
        used=used,
        unit=currency,
    )