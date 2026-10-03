"""Concurrent provider fetching with timeouts."""

import asyncio

import httpx

from .adapters import get
from .config import ProviderConfig, resolve_credential
from .records import UsageRecord, make_error_record


async def fetch_one(
    client: httpx.AsyncClient,
    config: ProviderConfig,
    timeout: float,
) -> list[UsageRecord]:
    """Fetch usage for a single provider with timeout."""
    try:
        credential = resolve_credential(config.key_env)
    except ValueError as e:
        return [make_error_record(config.name, str(e))]

    adapter = get(config.name)

    try:
        records = await asyncio.wait_for(
            asyncio.to_thread(adapter, credential),
            timeout=timeout,
        )
        # Ensure we have a list
        if not isinstance(records, list):
            records = [records]
        # Attach budget from config
        for r in records:
            if r.budget is None and config.budget is not None:
                r.budget = config.budget
        return records
    except asyncio.TimeoutError:
        return [make_error_record(config.name, f"timeout after {timeout}s")]
    except Exception as e:  # noqa: BLE001
        return [make_error_record(config.name, f"{type(e).__name__}: {e}")]


async def fetch_all(
    providers: list[ProviderConfig],
    request_timeout: float = 10.0,
    total_timeout: float = 30.0,
) -> list[UsageRecord]:
    """Fetch usage for all providers concurrently with timeouts."""
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(request_timeout)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        tasks = [
            fetch_one(client, pc, request_timeout) for pc in providers
        ]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=total_timeout,
            )
            # Flatten list of lists
            flat = []
            for r in results:
                flat.extend(r)
            return flat
        except asyncio.TimeoutError:
            return [
                make_error_record(
                    pc.name, f"total timeout after {total_timeout}s"
                )
                for pc in providers
            ]