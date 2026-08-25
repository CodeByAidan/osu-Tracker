"""Background services for polling Tosu and publishing Discord activity."""

import queue
import threading

import requests

from OsuTracker.discord_rpc import DiscordRPC
from OsuTracker.models.tosu import Model
from OsuTracker.settings import Settings
from OsuTracker.tosu import fetch_tosu_data

TrackerEvent = tuple[str, object]


def track(
    settings: Settings,
    stop_event: threading.Event,
    events: queue.Queue[TrackerEvent],
) -> None:
    """Poll Tosu until stopped, updating Discord and emitting UI events."""
    rpc = DiscordRPC(
        settings.client_id,
        settings.discord_details,
        settings.discord_state,
    )
    discord_connected = rpc.connect()
    events.put(
        (
            "status",
            "Tracking Tosu" + (" and Discord." if discord_connected else "."),
        )
    )
    try:
        while not stop_event.is_set():
            try:
                model = fetch_tosu_data(settings.endpoint)
            except requests.RequestException as error:
                events.put(("error", f"Unable to connect to Tosu: {error}"))
            except ValueError as error:
                events.put(("error", f"Unable to read Tosu data: {error}"))
            else:
                _publish_model(rpc, model, events)
            stop_event.wait(settings.interval)
    finally:
        rpc.close()
        events.put(("stopped", None))


def _publish_model(
    rpc: DiscordRPC,
    model: Model,
    events: queue.Queue[TrackerEvent],
) -> None:
    """Publish one successful Tosu response to Discord and the UI."""
    rpc.update(model)
    events.put(("model", model))
