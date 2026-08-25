"""Background services for checking and downloading application updates."""

import queue

import requests

from OsuTracker.updater import begin_windows_self_update, fetch_latest_release

UpdateEvent = tuple[str, object]


def check_for_update(manual: bool, events: queue.Queue[UpdateEvent]) -> None:
    """Fetch release metadata and report the result to the GUI event queue."""
    try:
        release = fetch_latest_release()
    except requests.RequestException as error:
        events.put(("update-error", (f"Unable to check updates: {error}", manual)))
        return
    except ValueError as error:
        events.put(("update-error", (f"Invalid update response: {error}", manual)))
        return
    events.put(("update-info", (release, manual)))


def download_update(
    download_url: str | None,
    events: queue.Queue[UpdateEvent],
) -> None:
    """Download an update and report progress and completion to the GUI."""
    if not download_url:
        events.put(("update-error", ("No release download URL found.", True)))
        return
    try:
        log_path = begin_windows_self_update(
            download_url,
            progress_callback=lambda downloaded, total: events.put(
                ("update-progress", (downloaded, total))
            ),
        )
    except requests.RequestException as error:
        events.put(("update-error", (f"Download failed: {error}", True)))
        return
    except OSError as error:
        events.put(("update-error", (f"Update failed: {error}", True)))
        return
    events.put(("update-started", log_path))
