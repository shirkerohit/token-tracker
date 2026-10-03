"""Provider adapter registry."""

from collections.abc import Callable

from ..records import UsageRecord

AdapterFunc = Callable[[str], UsageRecord]

_adapters: dict[str, AdapterFunc] = {}


def register(name: str, func: AdapterFunc) -> None:
    """Register a provider adapter by name."""
    _adapters[name.lower()] = func


def get(name: str) -> AdapterFunc:
    """Get an adapter by name, or raise KeyError with available names."""
    name_lc = name.lower()
    if name_lc not in _adapters:
        available = ", ".join(sorted(_adapters.keys()))
        raise KeyError(
            f"Unknown provider '{name}'. Available: {available}"
        )
    return _adapters[name_lc]


def available_names() -> list[str]:
    return sorted(_adapters.keys())


def _load_adapters() -> None:
    """Load and register all adapters."""
    from .anthropic import fetch_anthropic
    from .azure_openai import fetch_azure_openai
    from .cerebras import fetch_cerebras
    from .cohere import fetch_cohere
    from .deepseek import fetch_deepseek
    from .fireworks import fetch_fireworks
    from .github import fetch_github
    from .github_copilot import fetch_github_copilot
    from .google import fetch_google
    from .grok import fetch_grok
    from .mistral import fetch_mistral
    from .openai import fetch_openai
    from .openrouter import fetch_openrouter
    from .perplexity import fetch_perplexity
    from .together import fetch_together

    # Tier A: providers with real usage APIs
    register("openrouter", fetch_openrouter)       # USD credits + rate limits
    register("github", fetch_github)               # rate limit requests
    register("github_copilot", fetch_github_copilot) # Copilot subscription
    register("openai", fetch_openai)               # org admin key, USD
    register("anthropic", fetch_anthropic)         # admin key, USD
    register("together", fetch_together)           # USD
    register("fireworks", fetch_fireworks)         # USD
    register("google", fetch_google)               # Cloud Billing, USD
    register("azure_openai", fetch_azure_openai)   # Cost Management, USD
    register("grok", fetch_grok)                   # xAI, USD
    register("deepseek", fetch_deepseek)           # USD
    register("mistral", fetch_mistral)             # EUR
    register("cerebras", fetch_cerebras)           # USD
    register("cohere", fetch_cohere)               # USD
    register("perplexity", fetch_perplexity)       # USD


# Load adapters on module import
_load_adapters()