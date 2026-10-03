# quota

Local CLI tool to track quota usage across providers.

## Installation

```bash
pip install -e .
```

## Configuration

Create `~/.config/quota/config.yaml`:

```yaml
providers:
  - name: openrouter
    key_env: OPENROUTER_API_KEY
    budget: 50.0      # optional: local budget in USD for percentage
  - name: github
    key_env: GITHUB_TOKEN
    # budget: 5000    # optional: local budget in requests
```

Set the credential environment variables:

```bash
export OPENROUTER_API_KEY="sk-or-..."
export GITHUB_TOKEN="ghp_..."
```

## Usage

```bash
# Table output (default)
quota

# JSON output for scripting
quota --json

# Custom config path
quota --config /path/to/config.yaml
```

## Example Output

```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ PROVIDER   ┃        USED ┃     OF ┃ PCT ┃ RESETS ┃  FETCHED ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ openrouter │ 38.2 USD    │ 50 USD │ 76% │        │ 14:23:46 │
│ github     │ 188 requests│      - │   - │ 15:00  │ 14:23:47 │
└────────────┴─────────────┴────────┴─────┴────────┴──────────┘
```

- **USED**: Amount consumed in the provider's native unit (tokens, requests, USD, etc.)
- **OF**: Your declared budget (if any)
- **PCT**: Percentage of budget consumed (only shown when budget is set)
- **RESETS**: When the provider's quota resets (if reported)
- **FETCHED**: When this data was retrieved

## Supported Providers

| Provider | Unit | Notes |
|----------|------|-------|
| openrouter | USD | Requires `OPENROUTER_API_KEY` |
| github | requests | Requires `GITHUB_TOKEN` with `read:org` scope |

## Adding Providers

Each provider is a single function in `src/quota/adapters/`. Add a new file:

```python
# src/quota/adapters/myprovider.py
from quota.records import UsageRecord, make_error_record

def fetch_myprovider(api_key: str) -> UsageRecord:
    # ... fetch from API ...
    return UsageRecord(provider="myprovider", used=..., unit="...")
```

Then register in `src/quota/adapters/__init__.py`:

```python
from .myprovider import fetch_myprovider
register("myprovider", fetch_myprovider)
```

## Design

- **No daemon, no database, no history** — single-shot CLI
- **Credentials via env vars only** — never written to disk
- **Provider-native units** — no conversion, no fake percentages
- **Local budgets only** — percentage comes from your config, not the provider
- **Partial failure handling** — one provider failing doesn't hide the others

## License

MIT