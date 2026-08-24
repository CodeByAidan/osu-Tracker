"""Command-line entry point for the osu!Tracker workspace."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import time
from textwrap import dedent
from typing import Any

import requests

from OsuTracker.models.tosu import Model
from OsuTracker.discord_rpc import DiscordRPC
from OsuTracker.settings import (
    DEFAULT_ENDPOINT,
    DEFAULT_INTERVAL,
    configure_settings,
    default_settings_path,
    load_settings,
)

TOSU_ENDPOINT = DEFAULT_ENDPOINT


def fetch_tosu_data(
    endpoint: str = TOSU_ENDPOINT, timeout: float = 2.0
) -> dict[str, Any]:
    """Fetch the current game state from Tosu."""
    response = requests.get(endpoint, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Tosu returned a JSON value that is not an object")
    return data


def display_state(data: dict[str, Any]) -> None:
    """Display a readable snapshot while the tracker is being built out."""
    print(json.dumps(data, indent=2, sort_keys=True))


def display_main_stats(data: dict[str, Any]) -> None:
    """Display the main stats from the current game state."""
    try:
        model = Model.model_validate(data)
    except Exception as error:
        print(f"Unable to validate Tosu data: {error}", flush=True)
        return

    print(
        f"Current PP: {model.gameplay.pp.current} / " f"FC PP: {model.gameplay.pp.fc}",
        flush=True,
    )
    print(f"Max Combo: {model.gameplay.combo.max}", flush=True)
    print(f"Accuracy: {model.gameplay.accuracy:.2f}%", flush=True)
    print(f"Score: {model.gameplay.score}", flush=True)
    print(f"Mods: {model.menu.mods.str or 'None'}", flush=True)
    print(
        f"Map: {model.menu.bm.metadata.artist} - {model.menu.bm.metadata.title} [{model.menu.bm.metadata.difficulty}]",
        flush=True,
    )
    print(f"Mapper: {model.menu.bm.metadata.mapper}", flush=True)
    print(
        f"AR: {model.menu.bm.stats.AR}, CS: {model.menu.bm.stats.CS}, OD: {model.menu.bm.stats.OD}, HP: {model.menu.bm.stats.HP}",
        flush=True,
    )
    print(
        f"BPM: {model.menu.bm.stats.BPM.realtime} (min: {model.menu.bm.stats.BPM.min}, max: {model.menu.bm.stats.BPM.max})",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="osu-tracker",
        description="Show live osu! information from Tosu and publish it to Discord.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """\
            Examples:
              osu-tracker
              osu-tracker --client-id 123456789012345678
              osu-tracker --endpoint http://127.0.0.1:24050/json
              osu-tracker --once --no-discord
            """
        ),
    )

    tosu_options = parser.add_argument_group("Tosu connection")
    tosu_options.add_argument(
        "--endpoint",
        metavar="URL",
        help=f"Tosu JSON API URL (saved setting; default: {TOSU_ENDPOINT}).",
    )

    discord_options = parser.add_argument_group("Discord Rich Presence")
    discord_options.add_argument(
        "--client-id",
        metavar="APP_ID",
        help="Discord application ID for this run only.",
    )
    discord_options.add_argument(
        "--no-discord",
        action="store_true",
        help="Run without publishing a Discord activity.",
    )

    run_options = parser.add_argument_group("Run behavior")
    run_options.add_argument(
        "--interval",
        metavar="SECONDS",
        type=float,
        help=f"Seconds between updates for this run (saved default: {DEFAULT_INTERVAL:g}).",
    )
    run_options.add_argument(
        "--once",
        action="store_true",
        help="Fetch one Tosu snapshot, print it, then exit.",
    )
    settings_options = parser.add_argument_group("Saved settings")
    settings_options.add_argument(
        "--configure",
        action="store_true",
        help="Interactively save the Tosu endpoint, Discord app ID, and interval.",
    )
    settings_options.add_argument(
        "--settings-file",
        metavar="PATH",
        help="Use a different JSON settings file for this run.",
    )
    settings_options.add_argument(
        "--show-settings",
        action="store_true",
        help="Print the active settings and their file path, then exit.",
    )
    return parser.parse_args()


def run(
    endpoint: str, interval: float, once: bool, client_id: str | None, no_discord: bool
) -> int:
    if interval <= 0:
        print("Interval must be greater than zero.")
        return 2

    rpc = DiscordRPC(None if no_discord else client_id)
    rpc.connect()

    try:
        while True:
            try:
                data = fetch_tosu_data(endpoint)
                model = Model.model_validate(data)
            except requests.RequestException as error:
                print(f"Unable to connect to Tosu at {endpoint}: {error}", flush=True)
                if once:
                    return 1
            except (ValueError, json.JSONDecodeError) as error:
                print(f"Unable to read or validate Tosu data: {error}", flush=True)
                if once:
                    return 1
            else:
                print("\033[H\033[J", end="", flush=True)
                display_main_stats(data)
                rpc.update(model)
                if once:
                    return 0

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nTracker stopped.", flush=True)
        return 0
    finally:
        rpc.close()


def main() -> int:
    arguments = parse_args()
    settings_path = (
        Path(arguments.settings_file).expanduser()
        if arguments.settings_file
        else default_settings_path()
    )
    settings = load_settings(settings_path)

    if arguments.configure:
        configure_settings(settings, settings_path)
        return 0

    if arguments.show_settings:
        print(f"Settings file: {settings_path}")
        print(json.dumps(asdict(settings), indent=2))
        return 0

    client_id = arguments.client_id
    if client_id is None:
        client_id = settings.client_id or os.getenv("DISCORD_CLIENT_ID")
    return run(
        arguments.endpoint or settings.endpoint,
        arguments.interval if arguments.interval is not None else settings.interval,
        arguments.once,
        client_id,
        arguments.no_discord or not settings.discord_enabled,
    )


if __name__ == "__main__":
    raise SystemExit(main())
