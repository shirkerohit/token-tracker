"""xAI (Grok) adapter."""

import httpx

from quota.records import UsageRecord, make_error_record

# xAI does not currently have a public quota/usage endpoint.
# The usage field with cost_in_usd_ticks is returned per-model-call, not as a quota API.
BILLING_URL = "https://api.x.ai/v1/billing/usage"


def fetch_grok(api_key: str) -> UsageRecord:
    """Fetch usage from xAI.

    xAI does not currently expose a public quota/usage endpoint.
    The usage field (cost_in_usd_ticks) is returned per-model-call in the responses API,
    not as a separate quota endpoint.
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(BILLING_URL, headers=headers)
        if resp.status_code == 404:
            return make_error_record(
                "grok", "No public quota endpoint available (404). Usage tracked per-request via responses API."
            )
        if resp.status_code != 200:
            return make_error_record(
                "grok", f"billing: HTTP {resp.status_code}"
            )

        data = resp.json()
        # Expected format if endpoint exists: {"total_usage_usd": 123.45, "limit_usd": 500}
        used = data.get("total_usage_usd", data.get("total_usage", 0))
        limit = data.get("limit_usd", data.get("limit", None))
        currency = data.get("currency", "USD")

    return UsageRecord(
        provider="grok",
        used=used,
        unit=currency,
        provider_limit=limit,
    )