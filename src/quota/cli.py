"""Main CLI entry point."""

import argparse
import sys
from pathlib import Path

import yaml

from .adapters import available_names
from .config import DEFAULT_CONFIG_FILE, LOCAL_CONFIG_FILE, load_config
from .render import render_json, render_table
from .runner import fetch_all

PROVIDER_INFO = {
    "openrouter": ("OpenRouter (credits + rate limits)", "OPENROUTER_API_KEY"),
    "github": ("GitHub API rate limit", "GITHUB_TOKEN"),
    "github_copilot": ("GitHub Copilot subscription quota", "GITHUB_TOKEN"),
    "openai": ("OpenAI (requires org admin key)", "OPENAI_ADMIN_KEY"),
    "anthropic": ("Anthropic (requires admin key)", "ANTHROPIC_ADMIN_KEY"),
    "together": ("Together AI", "TOGETHER_API_KEY"),
    "fireworks": ("Fireworks AI", "FIREWORKS_API_KEY"),
    "google": ("Google Cloud Vertex AI", "GOOGLE_BILLING_KEY"),
    "azure_openai": ("Azure OpenAI", "AZURE_OPENAI_API_KEY"),
    "grok": ("xAI Grok", "XAI_API_KEY"),
    "deepseek": ("DeepSeek", "DEEPSEEK_API_KEY"),
    "mistral": ("Mistral", "MISTRAL_API_KEY"),
    "cerebras": ("Cerebras", "CEREBRAS_API_KEY"),
    "cohere": ("Cohere", "COHERE_API_KEY"),
    "perplexity": ("Perplexity", "PERPLEXITY_API_KEY"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quota",
        description="Track quota usage across providers",
    )
    # Global arguments available for all subcommands
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (default: ./config.yaml or ~/.config/quota/config.yaml)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # quota (default: show usage)
    _ = subparsers.add_parser("show", help="Show current usage (default)")

    # quota init - initial setup (creates new config)
    init_parser = subparsers.add_parser("init", help="Create new config file interactively")
    init_parser.add_argument(
        "--global",
        action="store_true",
        dest="global_config",
        help=f"Write to global config ({DEFAULT_CONFIG_FILE}) instead of local",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing config without prompting",
    )

    # quota add - add providers to existing config
    add_parser = subparsers.add_parser("add", help="Add providers to existing config")
    add_parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (default: ./config.yaml or ~/.config/quota/config.yaml)",
    )

    return parser


def _load_existing_config(config_path: Path) -> list[dict]:
    """Load existing config and return list of provider entries."""
    import yaml
    try:
        with config_path.open() as f:
            raw = yaml.safe_load(f) or {}
        return raw.get("providers", [])
    except (FileNotFoundError, yaml.YAMLError):
        return []


def _get_existing_names(config_path: Path) -> set[str]:
    """Get names of providers already in config."""
    existing = _load_existing_config(config_path)
    return {p.get("name") for p in existing if p.get("name")}


def _write_config(config_path: Path, providers: list[dict]) -> None:
    """Write providers list to config file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump({"providers": providers}, default_flow_style=False, sort_keys=False)
    config_path.write_text(content)


def cmd_init(args) -> int:
    """Create new config file interactively."""
    providers = available_names()
    config_path = Path(args.config) if args.config else (DEFAULT_CONFIG_FILE if args.global_config else LOCAL_CONFIG_FILE)

    # Check if config already exists
    if config_path.exists() and not args.force:
        print(f"Config already exists at: {config_path}")
        existing = _load_existing_config(config_path)
        if existing:
            print("Existing providers:")
            for p in existing:
                name = p.get("name", "?")
                budget = p.get("budget")
                print(f"  - {name}" + (f" (budget: {budget})" if budget else ""))
        print("\nOptions:")
        print("  1. Overwrite (create fresh)")
        print("  2. Append (add more providers) - use 'quota add' instead")
        print("  3. Cancel")
        try:
            choice = input("> ").strip()
        except EOFError:
            return 1
        if choice == "2":
            return cmd_add(args)
        if choice != "1":
            print("Cancelled")
            return 1

    print("Available providers:\n")
    for i, name in enumerate(providers, 1):
        desc, env_var = PROVIDER_INFO.get(name, ("", ""))
        print(f"  {i:2}. {name:<20} — {desc}")
        if env_var:
            print(f"      Env var: {env_var}")

    print("\nEnter provider numbers to add (comma-separated), or 'all': ")
    try:
        choice = input("> ").strip()
    except EOFError:
        return 1

    if choice.lower() == "all":
        selected = providers
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            selected = [providers[i] for i in indices if 0 <= i < len(providers)]
        except (ValueError, IndexError):
            print("Invalid selection")
            return 1

    if not selected:
        print("No providers selected")
        return 1

    print(f"\nWriting config to: {config_path}")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    new_entries = []
    for name in selected:
        env_var = PROVIDER_INFO.get(name, ("", ""))[1]
        entry = {"name": name, "key_env": env_var}
        try:
            budget = input(f"  Budget for {name} (optional, press Enter to skip): ").strip()
            if budget:
                entry["budget"] = float(budget)
        except EOFError:
            pass
        new_entries.append(entry)

    _write_config(config_path, new_entries)
    print(f"\nDone! Edit {config_path} to add your API keys to the environment.")
    print("Then run: quota show")
    return 0


def cmd_add(args) -> int:
    """Add providers to existing config."""
    providers = available_names()
    config_path = Path(args.config) if args.config else (LOCAL_CONFIG_FILE if LOCAL_CONFIG_FILE.exists() else DEFAULT_CONFIG_FILE)

    if not config_path.exists():
        print(f"No config found at {config_path}. Run 'quota init' first.")
        return 1

    existing_entries = _load_existing_config(config_path)
    existing_names = {p.get("name") for p in existing_entries if p.get("name")}

    print(f"Current config: {config_path}")
    print("Already configured:")
    for p in existing_entries:
        name = p.get("name", "?")
        budget = p.get("budget")
        print(f"  - {name}" + (f" (budget: {budget})" if budget else ""))

    # Show only providers not already configured
    available = [p for p in providers if p not in existing_names]
    if not available:
        print("\nAll providers already configured!")
        return 0

    print("\nAvailable to add:")
    for i, name in enumerate(available, 1):
        desc, env_var = PROVIDER_INFO.get(name, ("", ""))
        print(f"  {i:2}. {name:<20} — {desc}")
        if env_var:
            print(f"      Env var: {env_var}")

    print("\nEnter provider numbers to add (comma-separated), or 'all': ")
    try:
        choice = input("> ").strip()
    except EOFError:
        return 1

    if choice.lower() == "all":
        selected = available
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            selected = [available[i] for i in indices if 0 <= i < len(available)]
        except (ValueError, IndexError):
            print("Invalid selection")
            return 1

    if not selected:
        print("No providers selected")
        return 1

    # Add new entries
    for name in selected:
        env_var = PROVIDER_INFO.get(name, ("", ""))[1]
        entry = {"name": name, "key_env": env_var}
        try:
            budget = input(f"  Budget for {name} (optional, press Enter to skip): ").strip()
            if budget:
                entry["budget"] = float(budget)
        except EOFError:
            pass
        existing_entries.append(entry)

    _write_config(config_path, existing_entries)
    print(f"\nUpdated {config_path}")
    print("Run: quota show")
    return 0


def cmd_show(args) -> int:
    config_path = Path(args.config) if args.config else None

    try:
        providers = load_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2

    if not providers:
        print("No providers configured. Run 'quota init' to set up.", file=sys.stderr)
        return 0

    try:
        records = asyncio_run(fetch_all(providers))
    except Exception as e:  # noqa: BLE001
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(render_json(records))
    else:
        print(render_table(records))

    if all(r.is_error for r in records):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Default to 'show' if no command given
    if args.command is None or args.command == "show":
        return cmd_show(args)
    elif args.command == "init":
        return cmd_init(args)
    elif args.command == "add":
        return cmd_add(args)
    else:
        parser.print_help()
        return 1


def asyncio_run(coro):
    """Run an async coroutine, handling event loop."""
    try:
        import asyncio

        return asyncio.run(coro)
    except RuntimeError:
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


if __name__ == "__main__":
    sys.exit(main())