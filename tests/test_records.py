"""Tests for UsageRecord and adapter registry."""

import pytest

from quota.adapters import available_names, get, register
from quota.records import UsageRecord, make_error_record, make_success_record


class TestUsageRecord:
    def test_success_record(self):
        r = make_success_record("openrouter", 1000.0, "tokens")
        assert r.provider == "openrouter"
        assert r.used == 1000.0
        assert r.unit == "tokens"
        assert r.error is None
        assert not r.is_error
        assert r.fetched_at is not None

    def test_error_record(self):
        r = make_error_record("github", "timeout")
        assert r.provider == "github"
        assert r.error == "timeout"
        assert r.used is None
        assert r.is_error

    def test_percentage_with_budget(self):
        r = make_success_record("openrouter", 38.0, "USD", budget=50.0)
        assert r.percentage == 76.0

    def test_percentage_over_budget(self):
        r = make_success_record("openrouter", 60.0, "USD", budget=50.0)
        assert r.percentage == 120.0

    def test_percentage_no_budget(self):
        r = make_success_record("openrouter", 1000.0, "tokens")
        assert r.percentage is None

    def test_validation_requires_used_or_error(self):
        with pytest.raises(ValueError, match="must have either used or error"):
            UsageRecord(provider="test")

    def test_validation_not_both(self):
        with pytest.raises(ValueError, match="cannot have both"):
            UsageRecord(provider="test", used=1.0, unit="tokens", error="err")

    def test_validation_requires_unit_when_used(self):
        with pytest.raises(ValueError, match="must have a unit"):
            UsageRecord(provider="test", used=1.0)


class TestAdapterRegistry:
    def setup_method(self):
        # Clear registry before each test
        from quota.adapters import _adapters
        _adapters.clear()

    def test_register_and_get(self):
        def dummy_adapter(key: str):
            return make_success_record("test", 1.0, "tokens")

        register("test", dummy_adapter)
        assert get("test") is dummy_adapter
        assert get("TEST") is dummy_adapter  # case insensitive

    def test_unknown_provider_lists_available(self):
        register("openrouter", lambda k: None)
        register("github", lambda k: None)

        with pytest.raises(KeyError, match="Unknown provider 'unknown'"):
            get("unknown")

    def test_available_names(self):
        register("openrouter", lambda k: None)
        register("github", lambda k: None)
        assert set(available_names()) == {"github", "openrouter"}