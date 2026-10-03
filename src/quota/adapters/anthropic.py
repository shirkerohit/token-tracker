"""Anthropic adapter (requires admin key)."""

import httpx

from quota.records import UsageRecord, make_error_record

USAGE_URL = "https://api.anthropic.com/v1/organizations/usage_report/messages"


def fetch_anthropic(admin_key: str) -> UsageRecord:
    """Fetch usage from Anthropic organization usage report.

    Requires an admin API key (sk-ant-admin...), not a regular user key.
    Returns usage in tokens and USD.
    """
    headers = {
        "x-api-key": admin_key,
        "anthropic-version": "2023-06-01",
    }

    # Get usage for current month
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
                "anthropic", f"usage: HTTP {resp.status_code} - needs admin key"
            )

        data = resp.json()
        # Anthropic: {"data": [{"input_tokens": 1000, "output_tokens": 500, "cost_usd": 0.01, ...}]}
        total_tokens = 0
        total_cost = 0.0
        for bucket in data.get("data", []):
            total_tokens += bucket.get("input_tokens", 0) + bucket.get("output_tokens", 0)
            total_cost += bucket.get("cost_usd", 0)

    # Return cost in USD as primary, tokens as secondary could be added
    return UsageRecord(
        provider="anthropic",
        used=total_cost,
        unit="USD",
    )