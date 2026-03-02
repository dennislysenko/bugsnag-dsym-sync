#!/usr/bin/env python3
"""Bugsnag dSYM upload interactive TUI wrapper."""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import questionary
from rich.console import Console
from rich.table import Table

console = Console()

CONFIG_PATH = Path.home() / ".config" / "bugsnag-dsym-sync" / "projects.json"
ARCHIVES_DIR = Path.home() / "Library" / "Developer" / "Xcode" / "Archives"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
#
# Config format:
# {
#   "projects": {
#     "Transcribe": {"api_key": "...", "archive_prefix": "Transcribe"}
#   },
#   "uploaded": ["Transcribe 2-28-26, 1.05 PM.xcarchive", ...]
# }

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"projects": {}, "uploaded": []}
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
        cfg.setdefault("uploaded", [])
        # Migrate old flat format: {"Transcribe": "api_key"} → {"Transcribe": {"api_key": ..., "archive_prefix": ...}}
        migrated = False
        for name, value in list(cfg.get("projects", {}).items()):
            if isinstance(value, str):
                cfg["projects"][name] = {"api_key": value, "archive_prefix": name}
                migrated = True
        if migrated:
            save_config(cfg)
        return cfg
    except (json.JSONDecodeError, OSError):
        console.print("[red]Warning: could not read config file, starting fresh.[/red]")
        return {"projects": {}, "uploaded": []}


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return key
    return key[:6] + "..." + key[-4:]


def mark_uploaded(config: dict, archive: Path) -> None:
    uploaded: list = config.setdefault("uploaded", [])
    if archive.name not in uploaded:
        uploaded.append(archive.name)
        save_config(config)


def is_uploaded(config: dict, archive: Path) -> bool:
    return archive.name in config.get("uploaded", [])


def get_project(config: dict, name: str) -> dict:
    """Return the project dict for a given project name."""
    return config["projects"][name]


# ---------------------------------------------------------------------------
# API key validation
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^[0-9a-f]{32}$")

def validate_api_key_format(key: str) -> bool:
    """Bugsnag project API keys are always 32 lowercase hex characters."""
    return bool(_KEY_RE.match(key))


# ---------------------------------------------------------------------------
# Archive discovery
# ---------------------------------------------------------------------------

def find_archives(archive_prefix: str, start: date, end: date) -> list[Path]:
    if not ARCHIVES_DIR.exists():
        return []
    results = []
    try:
        date_dirs = sorted(ARCHIVES_DIR.iterdir())
    except PermissionError:
        console.print("[red]Permission denied reading archives directory.[/red]")
        return []

    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue
        try:
            folder_date = date.fromisoformat(date_dir.name)
        except ValueError:
            continue
        if not (start <= folder_date <= end):
            continue
        try:
            for archive in date_dir.iterdir():
                if archive.suffix == ".xcarchive" and archive.name.startswith(archive_prefix):
                    results.append(archive)
        except PermissionError:
            continue

    return sorted(results, reverse=True)  # newest first


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_archive(archive: Path, api_key: str) -> bool:
    result = subprocess.run(
        ["bugsnag-dsym-upload", "--api-key", api_key, str(archive)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]  STDERR:[/red] {result.stderr.strip()}")
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Project management
# ---------------------------------------------------------------------------

def list_projects(config: dict) -> None:
    projects = config.get("projects", {})
    if not projects:
        console.print("[yellow]No projects configured.[/yellow]")
        return
    table = Table(title="Configured Projects", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Archive Prefix")
    table.add_column("API Key")
    for name, data in sorted(projects.items()):
        table.add_row(name, data.get("archive_prefix", name), mask_key(data["api_key"]))
    console.print(table)


def add_project(config: dict) -> None:
    console.print(
        "\n[dim]Find your project API key at "
        "[link=https://app.bugsnag.com/settings/]https://app.bugsnag.com/settings/[/link]"
        " → Projects (left sidebar) → click your project.[/dim]\n"
    )
    name = questionary.text("Project display name (e.g. 'Transcribe'):").ask()
    if not name:
        return
    name = name.strip()

    prefix = questionary.text(
        "Archive prefix (the start of its .xcarchive folder name):",
        default=name.replace(" ", ""),
    ).ask()
    if not prefix:
        return
    prefix = prefix.strip()

    while True:
        key = questionary.text("API key:").ask()
        if not key:
            return
        key = key.strip()
        if validate_api_key_format(key):
            console.print("[green]✓ Key format looks valid (32 hex chars).[/green]")
            break
        console.print(
            "[red]✗ Invalid format — Bugsnag project keys are 32 lowercase hex characters. "
            "Please try again.[/red]"
        )

    config.setdefault("projects", {})[name] = {"api_key": key, "archive_prefix": prefix}
    save_config(config)
    console.print(f"[green]Project '{name}' saved.[/green]")


def remove_project(config: dict) -> None:
    projects = config.get("projects", {})
    if not projects:
        console.print("[yellow]No projects to remove.[/yellow]")
        return
    choices = sorted(projects.keys()) + ["Cancel"]
    choice = questionary.select("Select project to remove:", choices=choices).ask()
    if not choice or choice == "Cancel":
        return
    confirmed = questionary.confirm(f"Remove '{choice}'?", default=False).ask()
    if confirmed:
        del config["projects"][choice]
        save_config(config)
        console.print(f"[green]Project '{choice}' removed.[/green]")


def manage_projects(config: dict) -> None:
    while True:
        action = questionary.select(
            "Manage projects:",
            choices=["Add project", "Remove project", "List projects", "Back"],
        ).ask()
        if action is None or action == "Back":
            break
        elif action == "Add project":
            add_project(config)
        elif action == "Remove project":
            remove_project(config)
        elif action == "List projects":
            list_projects(config)


# ---------------------------------------------------------------------------
# Sync all projects (7d)
# ---------------------------------------------------------------------------

def sync_all(config: dict, start: date, end: date) -> None:
    """Upload all archives not yet in local history, across every project."""
    projects = config.get("projects", {})
    if not projects:
        console.print(
            "[yellow]No projects configured. Use 'Manage projects' → 'Add project' first.[/yellow]"
        )
        return

    console.print(
        f"\n[dim]Note: upload history is local to this machine — archives uploaded from "
        f"another machine won't appear here.[/dim]"
    )

    with console.status("Scanning for unuploaded archives..."):
        pending: list[tuple[str, Path, str]] = []  # (display_name, archive, api_key)
        for proj_name, data in sorted(projects.items()):
            prefix = data.get("archive_prefix", proj_name)
            api_key = data["api_key"]
            for archive in find_archives(prefix, start, end):
                if not is_uploaded(config, archive):
                    pending.append((proj_name, archive, api_key))

    if not pending:
        console.print(
            "\n[green]✓ All archives for the past 7 days are already uploaded.[/green]"
        )
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Project", style="bold")
    table.add_column("Archive")
    table.add_column("Date")
    for proj_name, archive, _ in pending:
        table.add_row(proj_name, archive.name, archive.parent.name)
    console.print(table)

    confirmed = questionary.confirm(
        f"Upload {len(pending)} archive(s) across {len({p[0] for p in pending})} project(s)?",
        default=True,
    ).ask()
    if not confirmed:
        return

    console.print()
    success_count = 0
    for proj_name, archive, api_key in pending:
        console.print(f"[bold]{proj_name}[/bold]  {archive.name}")
        with console.status("  Running bugsnag-dsym-upload..."):
            ok = upload_archive(archive, api_key)
        if ok:
            console.print("  [green]✓ Success[/green]")
            mark_uploaded(config, archive)
            success_count += 1
        else:
            console.print("  [red]✗ Failed[/red]")

    console.print()
    console.print(
        f"[bold]Done:[/bold] {success_count}/{len(pending)} archives uploaded successfully."
    )


# ---------------------------------------------------------------------------
# Upload flow (single project)
# ---------------------------------------------------------------------------

def prompt_date_range(default_start: date, default_end: date) -> tuple[date, date]:
    console.print(
        f"[dim]Default date range:[/dim] [cyan]{default_start}[/cyan] → [cyan]{default_end}[/cyan]"
    )
    customize = questionary.confirm("Customize date range?", default=False).ask()
    if not customize:
        return default_start, default_end

    while True:
        start_str = questionary.text(
            "Start date (YYYY-MM-DD):", default=str(default_start)
        ).ask()
        try:
            start = date.fromisoformat(start_str.strip())
            break
        except (ValueError, AttributeError):
            console.print("[red]Invalid date format.[/red]")

    while True:
        end_str = questionary.text(
            "End date (YYYY-MM-DD):", default=str(default_end)
        ).ask()
        try:
            end = date.fromisoformat(end_str.strip())
            break
        except (ValueError, AttributeError):
            console.print("[red]Invalid date format.[/red]")

    return start, end


def upload_flow(config: dict, default_start: date, default_end: date) -> None:
    projects = config.get("projects", {})
    if not projects:
        console.print(
            "[yellow]No projects configured. Use 'Manage projects' → 'Add project' first.[/yellow]"
        )
        return

    proj_name = questionary.select(
        "Select project:", choices=sorted(projects.keys())
    ).ask()
    if not proj_name:
        return

    data = projects[proj_name]
    api_key = data["api_key"]
    prefix = data.get("archive_prefix", proj_name)

    start, end = prompt_date_range(default_start, default_end)

    with console.status("Scanning for archives..."):
        archives = find_archives(prefix, start, end)

    if not archives:
        console.print(
            f"[yellow]No archives found for '{proj_name}' (prefix: '{prefix}') "
            f"between {start} and {end}.[/yellow]"
        )
        return

    def archive_label(p: Path) -> str:
        tag = "  [dim][uploaded][/dim]" if is_uploaded(config, p) else ""
        return f"{p.name}  [{p.parent.name}]{tag}"

    choices = [
        questionary.Choice(title=archive_label(a), value=a, checked=not is_uploaded(config, a))
        for a in archives
    ]

    selected = questionary.checkbox(
        "Select archives to upload:", choices=choices
    ).ask()

    if not selected:
        console.print("[yellow]No archives selected.[/yellow]")
        return

    confirmed = questionary.confirm(
        f"Upload {len(selected)} archive(s) with key {mask_key(api_key)}?", default=True
    ).ask()
    if not confirmed:
        return

    console.print()
    success_count = 0
    for archive in selected:
        console.print(f"[bold]Uploading:[/bold] {archive.name}")
        with console.status("  Running bugsnag-dsym-upload..."):
            ok = upload_archive(archive, api_key)
        if ok:
            console.print("  [green]✓ Success[/green]")
            mark_uploaded(config, archive)
            success_count += 1
        else:
            console.print("  [red]✗ Failed[/red]")

    console.print()
    console.print(
        f"[bold]Done:[/bold] {success_count}/{len(selected)} archives uploaded successfully."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive Bugsnag dSYM upload wrapper"
    )
    parser.add_argument(
        "-d", "--days", type=int, default=7, metavar="DAYS",
        help="Days back from today (default: 7)"
    )
    parser.add_argument(
        "-s", "--start", type=str, default=None, metavar="YYYY-MM-DD",
        help="Start date override"
    )
    parser.add_argument(
        "-e", "--end", type=str, default=None, metavar="YYYY-MM-DD",
        help="End date override"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    today = date.today()

    default_end = today
    default_start = today - timedelta(days=args.days - 1)

    if args.end:
        try:
            default_end = date.fromisoformat(args.end)
        except ValueError:
            console.print(f"[red]Invalid end date: {args.end}[/red]")
            sys.exit(1)

    if args.start:
        try:
            default_start = date.fromisoformat(args.start)
        except ValueError:
            console.print(f"[red]Invalid start date: {args.start}[/red]")
            sys.exit(1)

    config = load_config()

    console.print("[bold cyan]Bugsnag dSYM Uploader[/bold cyan]\n")

    while True:
        action = questionary.select(
            "What would you like to do?",
            choices=["Sync all projects (7d)", "Upload archives", "Manage projects", "Quit"],
        ).ask()

        if action is None or action == "Quit":
            break
        elif action == "Sync all projects (7d)":
            sync_all(config, default_start, default_end)
        elif action == "Upload archives":
            upload_flow(config, default_start, default_end)
        elif action == "Manage projects":
            manage_projects(config)

        console.print()


if __name__ == "__main__":
    main()
