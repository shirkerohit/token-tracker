"""Tests for GitHub adapter."""

from unittest.mock import MagicMock, patch

from quota.adapters.github import fetch_github
from quota.records import UsageRecord


class TestGitHubAdapter:
    @patch("quota.adapters.github.httpx.Client")
    def test_success(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        import time
        reset_ts = int(time.time()) + 3600

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "resources": {
                "core": {"limit": 5000, "remaining": 4812, "reset": reset_ts}
            }
        }
        mock_client.get.return_value = resp

        record = fetch_github("test-token")

        assert isinstance(record, UsageRecord)
        assert record.provider == "github"
        assert record.used == 188  # 5000 - 4812
        assert record.unit == "requests"
        assert record.reset_at is not None

    @patch("quota.adapters.github.httpx.Client")
    def test_auth_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        resp = MagicMock()
        resp.status_code = 401
        mock_client.get.return_value = resp

        record = fetch_github("test-token")

        assert record.is_error
        assert "rate_limit: HTTP 401" in record.error

    @patch("quota.adapters.github.httpx.Client")
    def test_missing_fields(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"resources": {}}
        mock_client.get.return_value = resp

        record = fetch_github("test-token")

        # Should handle missing fields gracefully
        assert isinstance(record, UsageRecord)
        assert record.used == 5000  # limit - remaining (default 0)
        assert record.unit == "requests"