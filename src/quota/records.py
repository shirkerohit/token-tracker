"""Usage record types and helpers."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UsageRecord:
    """Uniform record returned by every provider adapter."""

    provider: str
    used: float | None = None
    unit: str | None = None
    reset_at: datetime | None = None
    fetched_at: datetime = field(default_factory=_now)
    error: str | None = None
    budget: float | None = None          # local budget from config
    provider_limit: float | None = None  # hard cap from provider API

    def __post_init__(self) -> None:
        """Ensure a record is either a success or an error, never both."""
        if self.used is None and self.error is None:
            raise ValueError("UsageRecord must have either used or error")
        if self.used is not None and self.error is not None:
            raise ValueError("UsageRecord cannot have both used and error")
        if self.used is not None and self.unit is None:
            raise ValueError("UsageRecord with used must have a unit")

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @property
    def has_budget(self) -> bool:
        return self.budget is not None and self.budget > 0

    @property
    def has_provider_limit(self) -> bool:
        return self.provider_limit is not None and self.provider_limit > 0

    @property
    def percentage(self) -> float | None:
        """Percentage against local budget (user-defined)."""
        if not self.has_budget or self.used is None:
            return None
        if self.budget == 0:
            return None
        return (self.used / self.budget) * 100

    @property
    def provider_percentage(self) -> float | None:
        """Percentage against provider's hard cap."""
        if not self.has_provider_limit or self.used is None:
            return None
        if self.provider_limit == 0:
            return None
        return (self.used / self.provider_limit) * 100


def make_error_record(provider: str, error: str) -> UsageRecord:
    """Create an error record for a provider that failed to fetch."""
    return UsageRecord(provider=provider, error=error, fetched_at=_now())


def make_success_record(
    provider: str,
    used: float,
    unit: str,
    reset_at: datetime | None = None,
    budget: float | None = None,
) -> UsageRecord:
    """Create a success record with current fetch time."""
    return UsageRecord(
        provider=provider,
        used=used,
        unit=unit,
        reset_at=reset_at,
        fetched_at=_now(),
        budget=budget,
    )