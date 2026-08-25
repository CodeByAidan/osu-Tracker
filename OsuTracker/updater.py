"""GitHub release update helpers for osu!Tracker."""

import importlib.metadata as metadata
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from OsuTracker import __version__

REPO_OWNER = "CodeByAidan"
REPO_NAME = "osu-Tracker"
LATEST_RELEASE_API = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
)
RELEASES_PAGE = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"


@dataclass(frozen=True)
class ReleaseInfo:
    """Information about the latest GitHub release."""

    tag: str
    version: str
    name: str
    body: str
    published_at: str
    exe_download_url: str | None


def current_version() -> str:
    """Return the currently running app version."""
    try:
        return metadata.version("osu-tracker")
    except metadata.PackageNotFoundError:
        return __version__


def _version_parts(value: str) -> tuple[int, ...]:
    text = value.strip().lstrip("v")
    parts: list[int] = []
    for chunk in text.split("."):
        number = ""
        for char in chunk:
            if char.isdigit():
                number += char
            else:
                break
        if not number:
            break
        parts.append(int(number))
    return tuple(parts) if parts else (0, 0, 0)


def is_update_available(current: str, latest: str) -> bool:
    """Compare semantic-looking versions with v-prefix support."""
    current_parts = _version_parts(current)
    latest_parts = _version_parts(latest)
    width = max(len(current_parts), len(latest_parts))
    return current_parts + (0,) * (width - len(current_parts)) < latest_parts + (0,) * (
        width - len(latest_parts)
    )


def _select_exe_download_url(assets: object) -> str | None:
    if not isinstance(assets, list):
        return None
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        asset_name = str(asset.get("name") or "").lower()
        if not asset_name.endswith(".exe"):
            continue
        url = str(asset.get("browser_download_url") or "").strip()
        if url:
            return url
    return None


def fetch_latest_release(timeout: float = 6.0) -> ReleaseInfo:
    """Fetch the latest release metadata from GitHub."""
    response = requests.get(
        LATEST_RELEASE_API,
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()

    tag = str(payload.get("tag_name") or "").strip()
    name = str(payload.get("name") or "").strip() or tag or "Latest release"
    body = str(payload.get("body") or "")
    published_at = str(payload.get("published_at") or "")
    version = tag.lstrip("v") if tag else "0.0.0"

    exe_download_url = _select_exe_download_url(payload.get("assets"))

    return ReleaseInfo(
        tag=tag,
        version=version,
        name=name,
        body=body,
        published_at=published_at,
        exe_download_url=exe_download_url,
    )


def _download_file(url: str, destination: Path, timeout: float = 30.0) -> None:
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    file.write(chunk)


def begin_windows_self_update(download_url: str) -> None:
    """Download a new exe and launch a helper script to replace this process."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Self-update is only supported in the packaged .exe.")

    current_exe = Path(sys.executable).resolve()
    update_dir = Path(tempfile.gettempdir()) / "osu-tracker-updater"
    update_dir.mkdir(parents=True, exist_ok=True)

    next_exe = update_dir / "osu-tracker-next.exe"
    script_path = update_dir / "apply-update.ps1"

    _download_file(download_url, next_exe)

    script_path.write_text(
        """param(
    [Parameter(Mandatory=$true)][string]$TargetExe,
    [Parameter(Mandatory=$true)][string]$NewExe,
    [Parameter(Mandatory=$true)][int]$PidToWait
)

$ErrorActionPreference = "Stop"

try {
    Wait-Process -Id $PidToWait -Timeout 30 -ErrorAction SilentlyContinue
} catch {}

Move-Item -Path $NewExe -Destination $TargetExe -Force
Start-Process -FilePath $TargetExe
""",
        encoding="utf-8",
    )

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-TargetExe",
            str(current_exe),
            "-NewExe",
            str(next_exe),
            "-PidToWait",
            str(os.getpid()),
        ],
        creationflags=creation_flags,
    )
