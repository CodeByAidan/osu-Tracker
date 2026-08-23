import time
import warnings
from typing import Optional

from pypresence.presence import Presence

from OsuTracker.models.tosu import Model

OSU_BEATMAP_COVER_URL = "https://assets.ppy.sh/beatmaps/{set_id}/covers/cover.jpg"
OSU_BEATMAP_URL = "https://osu.ppy.sh/beatmapsets/{set_id}"
OSU_LOGO_URL = (
    "https://i.ppy.sh/013ed2c11b34720790e74035d9f49078d5e9aa64/"
    "68747470733a2f2f6f73752e7070792e73682f77696b692f696d616765732f"
    "4272616e645f6964656e746974795f67756964656c696e65732f696d672f"
    "75736167652d66756c6c2d636f6c6f75722e706e67"
)

# pypresence can emit this harmless warning while Windows closes its IPC pipe
warnings.filterwarnings(
    "ignore", message="unclosed transport", category=ResourceWarning
)


class DiscordRPC:
    """Publish the current Tosu state as a Discord Rich Presence activity."""

    def __init__(self, client_id: Optional[str]) -> None:
        self.client_id = client_id
        self._presence: Optional[Presence] = None
        self._last_song_time: Optional[int] = None
        self._last_song_time_seen_at: Optional[float] = None

    @property
    def enabled(self) -> bool:
        return bool(self.client_id)

    def connect(self) -> bool:
        if not self.client_id:
            print(
                "Discord RPC disabled: set DISCORD_CLIENT_ID or pass --client-id.",
                flush=True,
            )
            return False

        try:
            self._presence = Presence(self.client_id)
            self._presence.connect()
        except Exception as error:
            self._presence = None
            print(f"Unable to connect to Discord RPC: {error}", flush=True)
            return False
        print("Discord RPC connected.", flush=True)
        return True

    def update(self, model: Model) -> None:
        if self._presence is None:
            return

        metadata = model.menu.bm.metadata
        activity_state = self._activity_state(model)
        if model.menu.state == 2:
            details = self._gameplay_details(model, activity_state)
            state = f"{metadata.artist} - {metadata.title}"
            large_image, large_text, large_url = self._beatmap_art(model)
        else:
            details = activity_state
            state = f"{metadata.artist} - {metadata.title}"
            large_image, large_text, large_url = OSU_LOGO_URL, "osu!", None

        try:
            self._presence.update(
                details=details[:128],
                state=state[:128],
                large_image=large_image,
                large_text=large_text[:128],
                large_url=large_url,
            )
        except Exception as error:
            print(f"Unable to update Discord RPC: {error}")
            self.close()

    @staticmethod
    def _beatmap_art(model: Model) -> tuple[str, str, str | None]:
        """Return Discord art fields for the selected beatmap.

        Discord accepts public image URLs for Rich Presence assets, so no
        per-map uploads to the Discord developer portal are required.
        """
        beatmap_set_id = model.menu.bm.set
        if beatmap_set_id <= 0:
            return OSU_LOGO_URL, "osu!", None

        metadata = model.menu.bm.metadata
        map_name = f"{metadata.artist} - {metadata.title}"
        return (
            OSU_BEATMAP_COVER_URL.format(set_id=beatmap_set_id),
            f"{map_name} [{metadata.difficulty}]",
            OSU_BEATMAP_URL.format(set_id=beatmap_set_id),
        )

    @staticmethod
    def _gameplay_details(model: Model, activity_state: str) -> str:
        """Build the compact live-stat line shown during a map."""
        hits = model.gameplay.hits
        total_time = model.menu.bm.time.full
        if total_time > 0:
            progress = min(
                100, max(0, round(model.menu.bm.time.current / total_time * 100))
            )
            progress_text = f"{progress}%"
        else:
            progress_text = "--%"

        return (
            f"{activity_state} | {model.menu.bm.stats.fullSR:.2f}★ "
            f"[{model.menu.bm.metadata.difficulty}] | "
            f"{model.menu.mods.str or 'NoMod'} | "
            f"{model.gameplay.accuracy:.2f}% | "
            f"PP {model.gameplay.pp.current:.0f}/{model.gameplay.pp.maxThisPlay:.0f} | "
            f"300x {hits.field_300} | 100x {hits.field_100} | "
            f"Max {model.gameplay.combo.max}x | {progress_text}"
        )

    def _activity_state(self, model: Model) -> str:
        """Classify Tosu's current screen for the Discord activity."""
        if model.menu.state != 2:
            self._last_song_time = None
            self._last_song_time_seen_at = None
            return "Scrolling for a new song"

        current_time = model.menu.bm.time.current
        now = time.monotonic()
        if current_time != self._last_song_time:
            self._last_song_time = current_time
            self._last_song_time_seen_at = now
            return "Playing"

        if (
            self._last_song_time_seen_at is not None
            and now - self._last_song_time_seen_at >= 2
        ):
            return "Paused"
        return "Playing"

    def close(self) -> None:
        presence = self._presence
        self._presence = None
        if presence is None:
            return

        loop = getattr(presence, "loop", None)
        writer = getattr(presence, "sock_writer", None)
        try:
            if writer is not None:
                presence.send_data(2, {"v": 1, "client_id": presence.client_id})
                if loop is not None and not loop.is_closed():
                    loop.run_until_complete(presence.read_output())
        except Exception:
            print("Error occurred while closing Discord RPC.")
            pass
        finally:
            if writer is not None:
                try:
                    writer.close()
                except Exception:
                    pass

                if loop is not None and not loop.is_closed():
                    try:
                        loop.run_until_complete(writer.wait_closed())
                    except Exception:
                        pass

            if loop is not None and not loop.is_closed():
                loop.close()
