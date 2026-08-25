"""Local configuration for osu!Tracker."""

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict

DEFAULT_ENDPOINT = "http://127.0.0.1:24050/json"
DEFAULT_INTERVAL = 5.0
DEFAULT_DISCORD_DETAILS = "gameplay"
DEFAULT_DISCORD_STATE = "map"
DISCORD_TEXT_OPTIONS = {
    "Gameplay summary": "gameplay",
    "Activity state": "activity",
    "Map title": "map",
    "Artist": "artist",
    "Difficulty": "difficulty",
    "Mods": "mods",
    "Accuracy": "accuracy",
    "Current PP": "pp",
    "Current combo": "combo",
    "Score": "score",
    "Player name": "player",
    "Star rating": "stars",
    "BPM": "bpm",
}


@dataclass
class Settings:
    """Preferences that persist between tracker runs."""

    endpoint: str = DEFAULT_ENDPOINT
    client_id: str | None = None
    interval: float = DEFAULT_INTERVAL
    discord_details: str = DEFAULT_DISCORD_DETAILS
    discord_state: str = DEFAULT_DISCORD_STATE


class SettingsDTO(TypedDict, total=False):
    """Typed shape of raw settings.json values before validation."""

    endpoint: object
    client_id: object
    interval: object
    discord_details: object
    discord_state: object


def default_settings_path() -> Path:
    """Return the per-user settings path without depending on the current folder."""
    if app_data := os.getenv("APPDATA"):
        return Path(app_data) / "osu-tracker" / "settings.json"
    if xdg_config := os.getenv("XDG_CONFIG_HOME"):
        return Path(xdg_config) / "osu-tracker" / "settings.json"
    return Path.home() / ".config" / "osu-tracker" / "settings.json"


def load_settings(path: Path) -> Settings:
    """Load valid settings from *path*, falling back to safe defaults."""
    if not path.exists():
        return Settings()

    try:
        with path.open(encoding="utf-8") as file:
            raw_data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Unable to read settings at {path}: {error}. Using defaults.")
        return Settings()

    data = _to_settings_dto(raw_data)
    if data is None:
        print(f"Settings at {path} must be a JSON object. Using defaults.")
        return Settings()

    return Settings(
        endpoint=_string_setting(data, "endpoint", DEFAULT_ENDPOINT),
        client_id=_optional_string_setting(data, "client_id"),
        interval=_interval_setting(data),
        discord_details=_discord_text_setting(
            data, "discord_details", DEFAULT_DISCORD_DETAILS
        ),
        discord_state=_discord_text_setting(
            data, "discord_state", DEFAULT_DISCORD_STATE
        ),
    )


def _to_settings_dto(raw_data: object) -> SettingsDTO | None:
    if not isinstance(raw_data, Mapping):
        return None

    data: SettingsDTO = {}
    for key in (
        "endpoint",
        "client_id",
        "interval",
        "discord_details",
        "discord_state",
    ):
        if key in raw_data:
            data[key] = raw_data[key]
    return data


def save_settings(settings: Settings, path: Path) -> None:
    """Save settings as readable JSON, creating the per-user folder if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(asdict(settings), file, indent=2)
        file.write("\n")


def configure_settings(current: Settings, path: Path) -> Settings:
    """Interactively update and persist user preferences."""
    print(f"Configuring osu!Tracker settings: {path}")
    endpoint = _prompt("Tosu API endpoint", current.endpoint)
    client_id = _prompt_optional(
        "Discord application ID (leave blank to disable)", current.client_id
    )
    interval = _prompt_interval(current.interval)
    settings = Settings(
        endpoint=endpoint,
        client_id=client_id or None,
        interval=interval,
        discord_details=_prompt_choice(
            "Discord Details", current.discord_details, DISCORD_TEXT_OPTIONS
        ),
        discord_state=_prompt_choice(
            "Discord State", current.discord_state, DISCORD_TEXT_OPTIONS
        ),
    )
    save_settings(settings, path)
    print("Settings saved.")
    return settings


def _string_setting(data: SettingsDTO, key: str, default: str) -> str:
    value = data.get(key, default)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _optional_string_setting(data: SettingsDTO, key: str) -> str | None:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _interval_setting(data: SettingsDTO) -> float:
    value = data.get("interval", DEFAULT_INTERVAL)
    if isinstance(value, bool):
        return DEFAULT_INTERVAL
    if not isinstance(value, (int, float, str)):
        return DEFAULT_INTERVAL
    try:
        interval = float(value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL
    return interval if interval > 0 else DEFAULT_INTERVAL


def _discord_text_setting(data: SettingsDTO, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value in DISCORD_TEXT_OPTIONS.values():
        return value
    return default


def _prompt(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def _prompt_optional(label: str, default: str | None) -> str:
    value = input(f"{label} [{default or ''}]: ").strip()
    return value


def _prompt_interval(default: float) -> float:
    while True:
        value = _prompt("Polling interval in seconds", f"{default:g}")
        try:
            interval = float(value)
        except ValueError:
            print("Enter a number greater than zero.")
            continue
        if interval > 0:
            return interval
        print("Enter a number greater than zero.")


def _prompt_choice(label: str, default: str, options: dict[str, str]) -> str:
    choices = list(options.items())
    print(f"{label}:")
    for index, (name, value) in enumerate(choices, start=1):
        marker = " (current)" if value == default else ""
        print(f"  {index}. {name}{marker}")
    while True:
        value = input("Choose an option [current]: ").strip()
        if not value:
            return default
        try:
            index = int(value) - 1
        except ValueError:
            index = -1
        if 0 <= index < len(choices):
            return choices[index][1]
        print("Choose one of the listed options.")
