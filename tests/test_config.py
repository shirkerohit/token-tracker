"""Tests for configuration loading and validation."""

import tempfile
from pathlib import Path

import pytest

from quota.config import ProviderConfig, load_config, resolve_credential


class TestProviderConfig:
    def test_from_dict_valid(self):
        pc = ProviderConfig.from_dict(
            {"name": "openrouter", "key_env": "OPENROUTER_API_KEY", "budget": 50.0}
        )
        assert pc.name == "openrouter"
        assert pc.key_env == "OPENROUTER_API_KEY"
        assert pc.budget == 50.0

    def test_from_dict_no_budget(self):
        pc = ProviderConfig.from_dict(
            {"name": "openrouter", "key_env": "OPENROUTER_API_KEY"}
        )
        assert pc.budget is None

    def test_from_dict_missing_name(self):
        with pytest.raises(ValueError, match="must have 'name' and 'key_env'"):
            ProviderConfig.from_dict({"key_env": "KEY"})

    def test_from_dict_missing_key_env(self):
        with pytest.raises(ValueError, match="must have 'name' and 'key_env'"):
            ProviderConfig.from_dict({"name": "openrouter"})


class TestResolveCredential:
    def test_resolves_set_variable(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "secret123")
        assert resolve_credential("TEST_KEY") == "secret123"

    def test_missing_variable(self):
        with pytest.raises(ValueError, match="credential not set: MISSING_KEY"):
            resolve_credential("MISSING_KEY")


class TestLoadConfig:
    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "config.yaml"
            with pytest.raises(FileNotFoundError):
                load_config(missing)

    def test_valid_config(self, tmp_path):
        config_content = """
providers:
  - name: openrouter
    key_env: OPENROUTER_API_KEY
    budget: 50
  - name: github
    key_env: GITHUB_TOKEN
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        # Register dummy adapters for validation
        from quota.adapters import register
        register("openrouter", lambda k: None)
        register("github", lambda k: None)

        providers = load_config(config_file)
        assert len(providers) == 2
        assert providers[0].name == "openrouter"
        assert providers[0].key_env == "OPENROUTER_API_KEY"
        assert providers[0].budget == 50.0
        assert providers[1].name == "github"
        assert providers[1].budget is None

    def test_empty_provider_list(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("providers: []")

        from quota.adapters import register
        register("openrouter", lambda k: None)

        providers = load_config(config_file)
        assert providers == []

    def test_unknown_provider(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "providers:\n  - name: unknown\n    key_env: KEY\n"
        )

        with pytest.raises(ValueError, match="not registered"):
            load_config(config_file)

    def test_malformed_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("providers: [")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_config(config_file)

    def test_provider_not_a_mapping(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("providers:\n  - not-a-mapping\n")

        from quota.adapters import register
        register("openrouter", lambda k: None)

        with pytest.raises(TypeError, match="must be a mapping"):
            load_config(config_file)