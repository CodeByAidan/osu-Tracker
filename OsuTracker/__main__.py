"""Command-line entry point for the osu!Tracker workspace."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

import requests

from OsuTracker.models.tosu import Model
from OsuTracker.discord_rpc import DiscordRPC

TOSU_ENDPOINT = "http://127.0.0.1:24050/json"
DEFAULT_INTERVAL = 5.0


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
    parser = argparse.ArgumentParser(description="Track osu! data from Tosu.")
    parser.add_argument("--endpoint", default=TOSU_ENDPOINT, help="Tosu JSON endpoint")
    parser.add_argument(
        "--client-id",
        default=os.getenv("DISCORD_CLIENT_ID"),
        help="Discord application client ID (default: DISCORD_CLIENT_ID)",
    )
    parser.add_argument(
        "--no-discord",
        action="store_true",
        help="Disable Discord Rich Presence",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help="Seconds between updates (default: %(default)s)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch and display one snapshot, then exit",
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
    return run(
        arguments.endpoint,
        arguments.interval,
        arguments.once,
        arguments.client_id,
        arguments.no_discord,
    )


if __name__ == "__main__":
    raise SystemExit(main())
