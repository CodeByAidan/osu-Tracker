"""Widgets and presentation logic for the Discord Rich Presence preview."""

import tkinter as tk
from io import BytesIO
from tkinter import ttk
from typing import Callable

import requests

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:  # pragma: no cover - optional at import-time
    Image = None
    ImageOps = None
    ImageTk = None

from OsuTracker.discord_rpc import OSU_LOGO_URL, DiscordRPC
from OsuTracker.models.tosu import Model

PREVIEW_CARD_BG = "#2B2D31"
PREVIEW_SUBTLE_TEXT = "#B5BAC1"
PREVIEW_MUTED_TEXT = "#949BA4"
PREVIEW_ELAPSED_TEXT = "#3BA55D"


class RichPresencePreview(ttk.LabelFrame):
    """Display a Discord-style preview for the latest Tosu model."""

    def __init__(
        self,
        parent: tk.Misc,
        activity_state_tracker: DiscordRPC,
        on_image_error: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            text="Discord Rich Presence preview",
            padding=12,
        )
        self._activity_state_tracker = activity_state_tracker
        self._on_image_error = on_image_error
        self._image_cache: dict[str, object] = {}
        self._image_label: tk.Label | None = None
        self._fallback_icon = tk.StringVar(self, value="♪")
        self._details = tk.StringVar(self, value="Waiting for Tosu data")
        self._state = tk.StringVar(
            self, value="Start tracking to preview Rich Presence"
        )
        self._activity = tk.StringVar(self, value="Not connected")
        self._elapsed = tk.StringVar(self, value="00:00 elapsed")
        self._large_text = tk.StringVar(self, value="osu!")
        self._status = tk.StringVar(
            self,
            value="Preview uses your current Details/State dropdown selection.",
        )
        self._current_image_url: str | None = None
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        card = tk.Frame(self, bg=PREVIEW_CARD_BG, padx=12, pady=12)
        card.grid(column=0, row=0, sticky="ew")
        card.columnconfigure(1, weight=1)

        tk.Label(
            card,
            text="Playing a Game",
            bg=PREVIEW_CARD_BG,
            fg=PREVIEW_SUBTLE_TEXT,
            font=("Comfortaa", 9),
        ).grid(column=0, row=0, columnspan=2, sticky="w", pady=(0, 8))

        image_slot = tk.Frame(
            card,
            width=72,
            height=72,
            bg="#1E1F22",
            highlightthickness=1,
            highlightbackground="#3F4248",
        )
        image_slot.grid(column=0, row=1, sticky="nw")
        image_slot.grid_propagate(False)
        self._image_label = tk.Label(
            image_slot,
            textvariable=self._fallback_icon,
            bg="#1E1F22",
            fg="#7A7D85",
            font=("Comfortaa", 18, "bold"),
        )
        self._image_label.place(relx=0.5, rely=0.5, anchor="center")

        preview_text = tk.Frame(card, bg=PREVIEW_CARD_BG)
        preview_text.grid(column=1, row=1, sticky="new", padx=(12, 0))
        preview_text.columnconfigure(0, weight=1)
        self._label(
            preview_text, "osu!Tracker", 0, "#FFFFFF", ("Comfortaa", 11, "bold")
        )
        self._label(
            preview_text, self._details, 1, "#FFFFFF", ("Comfortaa", 9), pady=(5, 0)
        )
        self._label(
            preview_text,
            self._state,
            2,
            PREVIEW_SUBTLE_TEXT,
            ("Comfortaa", 9),
            pady=(2, 0),
        )
        self._label(
            preview_text,
            self._elapsed,
            3,
            PREVIEW_ELAPSED_TEXT,
            ("Comfortaa", 9),
            pady=(4, 0),
        )
        tk.Label(
            self,
            textvariable=self._status,
            bg=self.winfo_toplevel().cget("bg"),
            fg=PREVIEW_MUTED_TEXT,
            font=("Comfortaa", 9),
            anchor="w",
            justify="left",
        ).grid(column=0, row=1, sticky="w", pady=(8, 0))

    @staticmethod
    def _label(
        parent: tk.Misc,
        value: str | tk.StringVar,
        row: int,
        foreground: str,
        font: tuple[str, int] | tuple[str, int, str],
        pady: tuple[int, int] = (0, 0),
    ) -> None:
        options: dict[str, object] = {
            "bg": PREVIEW_CARD_BG,
            "fg": foreground,
            "font": font,
            "anchor": "w",
            "justify": "left",
            "wraplength": 450,
        }
        if isinstance(value, tk.StringVar):
            options["textvariable"] = value
        else:
            options["text"] = value
        tk.Label(parent, **options).grid(column=0, row=row, sticky="w", pady=pady)

    def display(self, model: Model, details_field: str, state_field: str) -> None:
        """Render a Tosu model using the selected Discord text fields."""
        activity_state = self._activity_state_tracker.activity_state(model)
        self._activity.set(activity_state)
        self._details.set(
            DiscordRPC.text_value(model, details_field, activity_state)[:128]
        )
        self._state.set(DiscordRPC.text_value(model, state_field, activity_state)[:128])

        if model.menu.state == 2:
            image_url, large_text, _ = self._activity_state_tracker.beatmap_art(model)
        else:
            image_url, large_text = OSU_LOGO_URL, "osu!"
        self._large_text.set(large_text[:128])
        self._status.set(
            f"Activity: {activity_state}  |  Asset text: {self._large_text.get()}"
        )
        self._set_image(image_url)

        elapsed_seconds = max(0, int(model.menu.bm.time.current / 1000))
        minutes, seconds = divmod(elapsed_seconds, 60)
        self._elapsed.set(f"{minutes:02d}:{seconds:02d} elapsed")

    def _set_image(self, image_url: str) -> None:
        if self._image_label is None:
            return
        image = self._load_image(image_url, (72, 72))
        if image is None:
            self._image_label.configure(image="", textvariable=self._fallback_icon)
            self._image_label.image = None
            self._current_image_url = None
            return
        self._image_label.configure(image=image, text="")
        self._image_label.image = image
        self._current_image_url = image_url

    def _load_image(self, image_url: str, size: tuple[int, int]) -> object | None:
        if not image_url or image_url in self._image_cache:
            return self._image_cache.get(image_url)
        if Image is None or ImageOps is None or ImageTk is None:
            return None
        try:
            response = requests.get(image_url, timeout=4)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as raw_image:
                image = ImageOps.fit(
                    raw_image.convert("RGB"), size, method=Image.Resampling.LANCZOS
                )
            preview_image = ImageTk.PhotoImage(image)
        except requests.RequestException:
            return None
        except OSError:
            return None
        self._image_cache[image_url] = preview_image
        if len(self._image_cache) > 12:
            self._image_cache = dict(list(self._image_cache.items())[-8:])
        return preview_image
