"""Tests for OpenRouter adapter."""

from unittest.mock import MagicMock, patch

from quota.adapters.openrouter import fetch_openrouter
from quota.records import UsageRecord


class TestOpenRouterAdapter:
    @patch("quota.adapters.openrouter.httpx.Client")
    def test_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock credits response
        credits_resp = MagicMock()
        credits_resp.status_code = 200
        credits_resp.json.return_value = {
            "data": {"total_credits": 50, "total_usage": 38.2}
        }

        # Mock key response
        key_resp = MagicMock()
        key_resp.status_code = 200
        import time
        reset_ts = int(time.time()) + 3600
        key_resp.json.return_value = {
            "data": {"limit": 100, "remaining": 85, "reset": reset_ts}
        }

        mock_client.get.side_effect = [credits_resp, key_resp]

        record = fetch_openrouter("test-key")

        assert isinstance(record, UsageRecord)
        assert record.provider == "openrouter"
        assert record.used == 38.2
        assert record.unit == "USD"
        assert record.reset_at is not None

    @patch("quota.adapters.openrouter.httpx.Client")
    def test_credits_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        credits_resp = MagicMock()
        credits_resp.status_code = 401
        mock_client.get.return_value = credits_resp

        record = fetch_openrouter("test-key")

        assert record.is_error
        assert "credits: HTTP 401" in record.error

    @patch("quota.adapters.openrouter.httpx.Client")
    def test_no_reset_time(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        credits_resp = MagicMock()
        credits_resp.status_code = 200
        credits_resp.json.return_value = {"data": {"total_usage": 10.0}}

        key_resp = MagicMock()
        key_resp.status_code = 200
        key_resp.json.return_value = {"data": {"limit": 100, "remaining": 85}}

        mock_client.get.side_effect = [credits_resp, key_resp]

        record = fetch_openrouter("test-key")

        assert record.used == 10.0
        assert record.reset_at is None