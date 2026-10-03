"""Configuration loading and validation."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .adapters import available_names

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "quota"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
LOCAL_CONFIG_FILE = Path.cwd() / "config.yaml"


def find_config_file() -> Path:
    """Find config file, checking local first then default location."""
    if LOCAL_CONFIG_FILE.exists():
        return LOCAL_CONFIG_FILE
    return DEFAULT_CONFIG_FILE


@dataclass
class ProviderConfig:
    """Single provider configuration entry."""

    name: str
    key_env: str
    budget: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderConfig":
        if "name" not in data or "key_env" not in data:
            raise ValueError(
                "Provider entry must have 'name' and 'key_env'"
            )
        return cls(
            name=data["name"],
            key_env=data["key_env"],
            budget=data.get("budget"),
        )


def load_config(config_path: Path | None = None) -> list[ProviderConfig]:
    """Load and validate the provider configuration."""
    config_file = config_path or find_config_file()

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    try:
        with config_file.open() as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config: {e}")

    if "providers" not in raw:
        raise ValueError("Config must have a 'providers' list")

    if not isinstance(raw["providers"], list):
        raise TypeError("'providers' must be a list")

    known = set(available_names())
    providers = []

    for i, entry in enumerate(raw["providers"]):
        if not isinstance(entry, dict):
            raise TypeError(
                f"Provider at index {i} must be a mapping, got {type(entry).__name__}"
            )

        try:
            pc = ProviderConfig.from_dict(entry)
        except ValueError as e:
            raise ValueError(f"Provider at index {i}: {e}")

        if pc.name.lower() not in known:
            raise ValueError(
                f"Provider '{pc.name}' at index {i} is not registered. "
                f"Available: {', '.join(sorted(known))}"
            )

        providers.append(pc)

    return providers


def resolve_credential(key_env: str) -> str:
    """Resolve a credential from an environment variable."""
    value = os.environ.get(key_env)
    if value is None:
        raise ValueError(f"credential not set: {key_env}")
    return value