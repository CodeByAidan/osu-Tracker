"""Local configuration for osu!Tracker."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_ENDPOINT = "http://127.0.0.1:24050/json"
DEFAULT_INTERVAL = 5.0


@dataclass
class Settings:
    """Preferences that persist between tracker runs."""

    endpoint: str = DEFAULT_ENDPOINT
    client_id: str | None = None
    interval: float = DEFAULT_INTERVAL
    discord_enabled: bool = True


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
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Unable to read settings at {path}: {error}. Using defaults.")
        return Settings()

    if not isinstance(data, dict):
        print(f"Settings at {path} must be a JSON object. Using defaults.")
        return Settings()

    return Settings(
        endpoint=_string_setting(data, "endpoint", DEFAULT_ENDPOINT),
        client_id=_optional_string_setting(data, "client_id"),
        interval=_interval_setting(data),
        discord_enabled=_bool_setting(data, "discord_enabled", True),
    )


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
    discord_enabled = bool(client_id) and _prompt_yes_no(
        "Enable Discord Rich Presence", current.discord_enabled
    )

    settings = Settings(
        endpoint=endpoint,
        client_id=client_id or None,
        interval=interval,
        discord_enabled=discord_enabled,
    )
    save_settings(settings, path)
    print("Settings saved.")
    return settings


def _string_setting(data: dict[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _optional_string_setting(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _interval_setting(data: dict[str, Any]) -> float:
    value = data.get("interval", DEFAULT_INTERVAL)
    if isinstance(value, bool):
        return DEFAULT_INTERVAL
    try:
        interval = float(value)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL
    return interval if interval > 0 else DEFAULT_INTERVAL


def _bool_setting(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    return value if isinstance(value, bool) else default


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


def _prompt_yes_no(label: str, default: bool) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} [{default_text}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Enter y or n.")
