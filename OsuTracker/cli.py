"""Command-line interface for osu!Tracker."""

import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from textwrap import dedent

import requests

from OsuTracker.activity_state import activity_label, classify_activity_state
from OsuTracker.discord_rpc import DiscordRPC
from OsuTracker.models.tosu import Model
from OsuTracker.settings import (
    DEFAULT_ENDPOINT,
    DEFAULT_INTERVAL,
    configure_settings,
    default_settings_path,
    load_settings,
)
from OsuTracker.tosu import fetch_tosu_data


def display_main_stats(model: Model) -> None:
    """Print the main stats from the current game state."""
    print(
        f"Activity: {activity_label(classify_activity_state(model))}",
        flush=True,
    )
    print(
        f"Current PP: {model.gameplay.pp.current} / FC PP: {model.gameplay.pp.fc}",
        flush=True,
    )
    print(f"Max Combo: {model.gameplay.combo.max}", flush=True)
    print(f"Accuracy: {model.gameplay.accuracy:.2f}%", flush=True)
    print(f"Score: {model.gameplay.score}", flush=True)
    print(f"Mods: {model.menu.mods.str or 'None'}", flush=True)
    print(
        "Map: "
        f"{model.menu.bm.metadata.artist} - {model.menu.bm.metadata.title} "
        f"[{model.menu.bm.metadata.difficulty}]",
        flush=True,
    )
    print(f"Mapper: {model.menu.bm.metadata.mapper}", flush=True)
    print(
        f"AR: {model.menu.bm.stats.AR}, CS: {model.menu.bm.stats.CS}, "
        f"OD: {model.menu.bm.stats.OD}, HP: {model.menu.bm.stats.HP}",
        flush=True,
    )
    print(
        f"BPM: {model.menu.bm.stats.BPM.realtime} "
        f"(min: {model.menu.bm.stats.BPM.min}, max: {model.menu.bm.stats.BPM.max})",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    """Parse options for the terminal tracker."""
    parser = argparse.ArgumentParser(
        prog="osu-tracker-cli",
        description="Show live osu! information from Tosu in a terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            Examples:
              osu-tracker-cli
              osu-tracker-cli --client-id 123456789012345678
              osu-tracker-cli --endpoint http://127.0.0.1:24050/json
              osu-tracker-cli --once --no-discord
            """),
    )

    tosu_options = parser.add_argument_group("Tosu connection")
    tosu_options.add_argument(
        "--endpoint",
        metavar="URL",
        help=f"Tosu JSON API URL (saved setting; default: {DEFAULT_ENDPOINT}).",
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
    endpoint: str,
    interval: float,
    once: bool,
    client_id: str | None,
    no_discord: bool,
    discord_details: str,
    discord_state: str,
) -> int:
    """Poll Tosu and print results until stopped."""
    if interval <= 0:
        print("Interval must be greater than zero.")
        return 2

    rpc = DiscordRPC(
        None if no_discord else client_id,
        discord_details,
        discord_state,
    )
    rpc.connect()
    try:
        while True:
            try:
                model = fetch_tosu_data(endpoint)
            except requests.RequestException as error:
                print(f"Unable to connect to Tosu at {endpoint}: {error}", flush=True)
                if once:
                    return 1
            except ValueError as error:
                print(f"Unable to read or validate Tosu data: {error}", flush=True)
                if once:
                    return 1
            else:
                print("\033[H\033[J", end="", flush=True)
                display_main_stats(model)
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
    """Run the terminal application."""
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

    client_id = (
        arguments.client_id or settings.client_id or os.getenv("DISCORD_CLIENT_ID")
    )
    return run(
        arguments.endpoint or settings.endpoint,
        arguments.interval if arguments.interval is not None else settings.interval,
        arguments.once,
        client_id,
        arguments.no_discord,
        settings.discord_details,
        settings.discord_state,
    )


if __name__ == "__main__":
    raise SystemExit(main())
