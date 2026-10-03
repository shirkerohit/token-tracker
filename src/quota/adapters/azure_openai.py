"""Azure OpenAI adapter."""


from quota.records import UsageRecord, make_error_record


def fetch_azure_openai(api_key: str) -> UsageRecord:
    """Fetch usage from Azure OpenAI.

    Requires:
    - AZURE_OPENAI_ENDPOINT: e.g. https://myresource.openai.azure.com
    - AZURE_OPENAI_API_KEY: the API key
    - AZURE_OPENAI_API_VERSION: e.g. 2024-02-01

    Azure doesn't have a direct usage API like OpenAI.
    Returns usage from the deployment metrics if available.
    """
    import os
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

    if not endpoint:
        return make_error_record(
            "azure_openai", "AZURE_OPENAI_ENDPOINT env var not set"
        )

    # Azure OpenAI doesn't have a public usage endpoint
    # This would require Azure Monitor / Cost Management APIs
    return UsageRecord(
        provider="azure_openai",
        used=0.0,
        unit="USD",
        error="Azure OpenAI usage requires Azure Cost Management API",
    )