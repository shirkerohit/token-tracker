"""OpenAI adapter (requires org admin key)."""

import httpx

from quota.records import UsageRecord, make_error_record

USAGE_URL = "https://api.openai.com/v1/organization/usage"


def fetch_openai(admin_key: str) -> UsageRecord:
    """Fetch usage from OpenAI organization usage endpoint.

    Requires an org admin API key (sk-admin-...), not a regular project key.
    Returns usage in USD.
    """
    headers = {"Authorization": f"Bearer {admin_key}"}

    # Get usage for the current month
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    start_date = now.replace(day=1).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "bucket_width": "1d",
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(USAGE_URL, headers=headers, params=params)
        if resp.status_code != 200:
            return make_error_record(
                "openai", f"usage: HTTP {resp.status_code} - needs org admin key"
            )

        data = resp.json()
        # OpenAI usage: {"object": "list", "data": [{"amount": {"value": 123.45, "currency": "USD"}, ...}]}
        total = 0.0
        currency = "USD"
        for bucket in data.get("data", []):
            amount = bucket.get("amount", {})
            total += amount.get("value", 0)
            currency = amount.get("currency", "USD")

    return UsageRecord(
        provider="openai",
        used=total,
        unit=currency,
    )