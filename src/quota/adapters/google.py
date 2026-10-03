"""Google Cloud / Vertex AI adapter (uses Cloud Billing API)."""

import httpx

from quota.records import UsageRecord, make_error_record


def fetch_google(billing_key: str) -> UsageRecord:
    """Fetch usage from Google Cloud Billing API.

    Requires a Google Cloud service account with Billing Account Viewer role,
    and the billing account ID set in GOOGLE_BILLING_ACCOUNT env var.

    Returns usage in USD for Generative AI services.
    """
    import os
    billing_account = os.environ.get("GOOGLE_BILLING_ACCOUNT")
    if not billing_account:
        return make_error_record(
            "google", "GOOGLE_BILLING_ACCOUNT env var not set"
        )

    # Cloud Billing API - list project billing info
    url = f"https://cloudbilling.googleapis.com/v1/billingAccounts/{billing_account}/projects"

    headers = {"Authorization": f"Bearer {billing_key}"}

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code != 200:
            return make_error_record(
                "google", f"billing: HTTP {resp.status_code}"
            )

        _ = resp.json()
        # This returns project billing info, not detailed usage by service
        # For detailed usage, need Cloud Logging / BigQuery export
        # This is a simplified version

    return UsageRecord(
        provider="google",
        used=0.0,
        unit="USD",
        error="Google Cloud Billing requires BigQuery export for detailed usage",
    )