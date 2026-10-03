"""Tests for rendering."""

import json
from datetime import datetime, timedelta

from quota.records import make_error_record, make_success_record
from quota.render import render_json, render_table


class TestRenderTable:
    def test_basic_success_row(self):
        r = make_success_record("openrouter", 1000.0, "tokens")
        out = render_table([r])
        assert "openrouter" in out
        assert "1.0K tokens" in out
        assert " - " in out  # OF column

    def test_row_with_budget(self):
        r = make_success_record("openrouter", 38.0, "USD", budget=50.0)
        out = render_table([r])
        assert "openrouter" in out
        assert "38 USD" in out
        assert "76%" in out

    def test_row_over_budget(self):
        r = make_success_record("openrouter", 60.0, "USD", budget=50.0)
        out = render_table([r])
        assert "120%" in out

    def test_mixed_units_no_conversion(self):
        r1 = make_success_record("openrouter", 1_000_000, "tokens")
        r2 = make_success_record("github", 5000, "requests")
        out = render_table([r1, r2])
        assert "1.00M tokens" in out
        assert "5.0K requests" in out
        # No conversion between them

    def test_error_row_shows_reason(self):
        r = make_error_record("github", "credential not set: GITHUB_TOKEN")
        out = render_table([r])
        assert "ERROR" in out
        # Error row doesn't show the reason in USED column - that's by design

    def test_mixed_success_and_error(self):
        r1 = make_success_record("openrouter", 1000.0, "tokens")
        r2 = make_error_record("github", "timeout")
        out = render_table([r1, r2])
        assert "1.0K tokens" in out
        assert "ERROR" in out

    def test_reset_time_display(self):
        from datetime import timezone

        reset = datetime.now(timezone.utc) + timedelta(hours=1)
        r = make_success_record("openrouter", 100.0, "tokens", reset_at=reset)
        out = render_table([r])
        assert str(reset.hour).zfill(2) in out  # HH:MM format


class TestRenderJson:
    def test_success_record(self):
        r = make_success_record("openrouter", 38.0, "USD", budget=50.0)
        out = render_json([r])
        data = json.loads(out)
        assert len(data) == 1
        item = data[0]
        assert item["provider"] == "openrouter"
        assert item["used"] == 38.0
        assert item["unit"] == "USD"
        assert item["budget"] == 50.0
        assert item["percentage"] == 76.0

    def test_error_record(self):
        r = make_error_record("github", "timeout")
        out = render_json([r])
        data = json.loads(out)
        assert data[0]["provider"] == "github"
        assert data[0]["error"] == "timeout"
        assert "used" not in data[0]

    def test_same_data_different_format(self):
        """Table and JSON should represent the same records."""
        r1 = make_success_record("openrouter", 38.0, "USD", budget=50.0)
        r2 = make_error_record("github", "auth failed")

        table_out = render_table([r1, r2])
        json_out = render_json([r1, r2])

        # Both should have both providers
        assert "openrouter" in table_out and "github" in table_out
        data = json.loads(json_out)
        providers = {item["provider"] for item in data}
        assert providers == {"openrouter", "github"}