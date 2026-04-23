"""Rich table formatting utilities for 川流/UnendingX CLI."""

import json

import click
from rich.console import Console
from rich.json import JSON as RichJson
from rich.table import Table

console = Console()


def print_table(headers: list[str], rows: list[list], title: str | None = None) -> None:
    """Print a formatted table using rich.

    Args:
        headers: Column header names.
        rows: List of row data (each row is a list of values).
        title: Optional table title.
    """
    table = Table(title=title, show_lines=False, header_style="bold cyan")

    for header in headers:
        table.add_column(header)

    for row in rows:
        # Convert all values to strings for display
        str_row = [str(v) if v is not None else "" for v in row]
        table.add_row(*str_row)

    console.print(table)


def print_json(data: dict | list) -> None:
    """Pretty-print JSON data using rich."""
    console.print(RichJson.from_data(data, indent=2))


def print_error(msg: str) -> None:
    """Print an error message in red.

    Args:
        msg: Error message text.
    """
    click.secho(f"[X] {msg}", fg="red", bold=True)


def print_success(msg: str) -> None:
    """Print a success message in green.

    Args:
        msg: Success message text.
    """
    click.secho(f"[OK] {msg}", fg="green", bold=True)
