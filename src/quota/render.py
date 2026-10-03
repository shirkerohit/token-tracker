"""Rendering usage records to terminal table or JSON."""

import json
from datetime import datetime

from rich.console import Console
from rich.table import Table

from .records import UsageRecord


def render_table(records: list[UsageRecord]) -> str:
    """Render records as a terminal table."""
    console = Console(record=True, width=120)
    table = Table(show_header=True, header_style="bold", show_lines=False)

    table.add_column("PROVIDER", style="cyan", no_wrap=True)
    table.add_column("USED", justify="right")
    table.add_column("OF", justify="right")
    table.add_column("PCT", justify="right")
    table.add_column("RESETS", justify="right")
    table.add_column("FETCHED", justify="right")

    for r in records:
        if r.is_error:
            table.add_row(
                r.provider,
                "[red]ERROR[/red]",
                "-",
                "-",
                "-",
                _fmt_time(r.fetched_at),
                style="red",
            )
            continue

        used_str = _fmt_number(r.used)
        unit = r.unit or ""
        used_display = f"{used_str} {unit}".strip()

        # Determine what to show in OF/PCT columns
        # Priority: provider_limit > local budget > nothing
        if r.has_provider_limit:
            limit_str = _fmt_number(r.provider_limit)
            pct = r.provider_percentage
            pct_str = f"{pct:.0f}%" if pct is not None else "-"
            of_display = f"{limit_str} {unit}".strip()
            table.add_row(
                r.provider,
                used_display,
                of_display,
                pct_str,
                _fmt_reset(r.reset_at),
                _fmt_time(r.fetched_at),
            )
        elif r.has_budget:
            budget_str = _fmt_number(r.budget)
            pct = r.percentage
            pct_str = f"{pct:.0f}%" if pct is not None else "-"
            table.add_row(
                r.provider,
                used_display,
                f"{budget_str} {unit}".strip(),
                pct_str,
                _fmt_reset(r.reset_at),
                _fmt_time(r.fetched_at),
            )
        else:
            table.add_row(
                r.provider,
                used_display,
                "-",
                "-",
                _fmt_reset(r.reset_at),
                _fmt_time(r.fetched_at),
            )

    with console.capture() as capture:
        console.print(table)
    return capture.get()


def render_json(records: list[UsageRecord]) -> str:
    """Render records as JSON."""
    data = []
    for r in records:
        item = {
            "provider": r.provider,
            "fetched_at": r.fetched_at.isoformat(),
        }
        if r.is_error:
            item["error"] = r.error
        else:
            item["used"] = r.used
            item["unit"] = r.unit
            if r.reset_at:
                item["reset_at"] = r.reset_at.isoformat()
            if r.budget is not None:
                item["budget"] = r.budget
                if r.percentage is not None:
                    item["percentage"] = r.percentage
            if r.provider_limit is not None:
                item["provider_limit"] = r.provider_limit
                if r.provider_percentage is not None:
                    item["provider_percentage"] = r.provider_percentage
        data.append(item)
    return json.dumps(data, indent=2)


def _fmt_number(n: float | None) -> str:
    if n is None:
        return "-"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}"


def _fmt_reset(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")