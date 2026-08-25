"""Desktop interface for osu!Tracker."""

import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from ctypes import windll
from io import BytesIO
from pathlib import Path
from tkinter import messagebox, ttk

import requests

try:
    from PIL import Image, ImageOps, ImageTk
except (
    ImportError
):  # pragma: no cover - optional at import-time, required at runtime for image previews
    Image = None
    ImageOps = None
    ImageTk = None

from OsuTracker.activity_state import activity_label, classify_activity_state
from OsuTracker.discord_rpc import OSU_LOGO_URL, DiscordRPC
from OsuTracker.models.tosu import Model
from OsuTracker.settings import (
    DEFAULT_DISCORD_DETAILS,
    DEFAULT_DISCORD_STATE,
    DISCORD_TEXT_OPTIONS,
    Settings,
    default_settings_path,
    load_settings,
    save_settings,
)
from OsuTracker.tosu import fetch_tosu_data
from OsuTracker.updater import (
    RELEASES_PAGE,
    begin_windows_self_update,
    current_version,
    fetch_latest_release,
    is_update_available,
)

LINK_BUTTON_STYLE = "Link.TButton"
PREVIEW_CARD_BG = "#2B2D31"
PREVIEW_SUBTLE_TEXT = "#B5BAC1"
PREVIEW_MUTED_TEXT = "#949BA4"
PREVIEW_ELAPSED_TEXT = "#3BA55D"


def _load_comfortaa(font_path: Path) -> None:
    if os.name == "nt":
        try:
            windll.gdi32.AddFontResourceExW(str(font_path), 0x10, 0)
        except (AttributeError, OSError):
            pass


class TrackerApp(tk.Tk):
    """A small desktop app for configuring and running the tracker."""

    def __init__(self, settings: Settings, settings_path: Path) -> None:
        super().__init__()
        resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        theme_path = resource_root / "assets" / "azure" / "azure.tcl"
        self.tk.call("source", str(theme_path))
        self.tk.call("set_theme", "dark")
        _load_comfortaa(resource_root / "assets" / "fonts" / "Comfortaa[wght].ttf")
        style = ttk.Style(self)
        style.configure(".", font=("Comfortaa", 10))
        style.configure(
            "Map.TLabel", font=("Comfortaa", 12, "bold"), foreground="#ff66aa"
        )
        style.configure("Status.TLabel", foreground="#ff66aa")
        style.configure("Footer.TLabel", foreground="#a0a0a0", font=("Comfortaa", 9))
        style.configure(LINK_BUTTON_STYLE, padding=0, font=("Comfortaa", 9))
        style.map(
            LINK_BUTTON_STYLE,
            foreground=[
                ("disabled", "#6e6e6e"),
                ("active", "#9bd5ff"),
                ("!disabled", "#7ab7ff"),
            ],
        )
        self.title("osu!Tracker")
        try:
            self.iconbitmap(str(resource_root / "images" / "osu-tracker.ico"))
        except tk.TclError:
            pass
        self.minsize(660, 560)
        self.settings_path = settings_path
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None

        self.endpoint = tk.StringVar(value=settings.endpoint)
        self.client_id = tk.StringVar(value=settings.client_id or "")
        self.interval = tk.StringVar(value=f"{settings.interval:g}")
        self.discord_details = tk.StringVar(
            value=self._discord_option_name(settings.discord_details)
        )
        self.discord_state = tk.StringVar(
            value=self._discord_option_name(settings.discord_state)
        )
        self.status = tk.StringVar(
            value="Ready. Configure settings, then start tracking."
        )
        self.update_status = tk.StringVar(
            value=f"Current version: v{current_version()}"
        )
        self.current_version = current_version()
        self.latest_release_version: str | None = None
        self.latest_release_url: str | None = None
        self.preview_activity = tk.StringVar(value="Not connected")
        self.preview_details = tk.StringVar(value="Waiting for Tosu data")
        self.preview_state = tk.StringVar(
            value="Start tracking to preview Rich Presence"
        )
        self.preview_large_text = tk.StringVar(value="osu!")
        self.preview_elapsed = tk.StringVar(value="00:00 elapsed")
        self.preview_image_label: tk.Label | None = None
        self.preview_image_cache: dict[str, object] = {}
        self.preview_current_image_url: str | None = None
        self.preview_status_text = tk.StringVar(
            value="Preview uses your current Details/State dropdown selection."
        )
        self.preview_fallback_icon = tk.StringVar(value="♪")
        self.preview_state_tracker = DiscordRPC(settings.client_id)
        self.latest_model: Model | None = None

        self.discord_details.trace_add("write", self._refresh_preview_from_latest_model)
        self.discord_state.trace_add("write", self._refresh_preview_from_latest_model)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._process_events)
        self.after(800, self._check_for_update_background)

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        settings_frame = ttk.LabelFrame(container, text="Settings", padding=12)
        settings_frame.grid(column=0, row=0, columnspan=3, sticky="ew")
        settings_frame.columnconfigure(1, weight=1)
        self._setting_row(settings_frame, 0, "Tosu API endpoint", self.endpoint)
        self._setting_row(settings_frame, 1, "Discord application ID", self.client_id)
        self._setting_row(settings_frame, 2, "Update interval (seconds)", self.interval)
        self._discord_dropdown(
            settings_frame, 3, "Discord Details", self.discord_details
        )
        self._discord_dropdown(settings_frame, 4, "Discord State", self.discord_state)
        ttk.Label(
            settings_frame,
            text=f"Saved locally: {self.settings_path}",
            wraplength=590,
        ).grid(column=0, row=5, columnspan=2, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(container)
        buttons.grid(column=0, row=1, columnspan=3, sticky="ew", pady=12)
        ttk.Button(buttons, text="Save settings", command=self._save).pack(side="left")
        self.start_button = ttk.Button(
            buttons, text="Start tracking", command=self._start
        )
        self.start_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            buttons, text="Stop", command=self._stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))
        ttk.Label(container, textvariable=self.status, style="Status.TLabel").grid(
            column=0, row=2, columnspan=3, sticky="w", pady=(0, 12)
        )

        activity = ttk.LabelFrame(
            container,
            text="Discord Rich Presence preview",
            padding=12,
        )
        activity.grid(column=0, row=3, columnspan=3, sticky="nsew")
        container.rowconfigure(3, weight=1)
        activity.columnconfigure(0, weight=1)

        self.preview_card = tk.Frame(activity, bg=PREVIEW_CARD_BG, padx=12, pady=12)
        self.preview_card.grid(column=0, row=0, sticky="ew")
        self.preview_card.columnconfigure(1, weight=1)

        tk.Label(
            self.preview_card,
            text="Playing a Game",
            bg=PREVIEW_CARD_BG,
            fg=PREVIEW_SUBTLE_TEXT,
            font=("Comfortaa", 9),
        ).grid(column=0, row=0, columnspan=2, sticky="w", pady=(0, 8))

        image_slot = tk.Frame(
            self.preview_card,
            width=72,
            height=72,
            bg="#1E1F22",
            highlightthickness=1,
            highlightbackground="#3F4248",
        )
        image_slot.grid(column=0, row=1, sticky="nw")
        image_slot.grid_propagate(False)

        self.preview_image_label = tk.Label(
            image_slot,
            textvariable=self.preview_fallback_icon,
            bg="#1E1F22",
            fg="#7A7D85",
            font=("Comfortaa", 18, "bold"),
        )
        self.preview_image_label.place(relx=0.5, rely=0.5, anchor="center")

        preview_text = tk.Frame(self.preview_card, bg=PREVIEW_CARD_BG)
        preview_text.grid(column=1, row=1, sticky="new", padx=(12, 0))
        preview_text.columnconfigure(0, weight=1)

        tk.Label(
            preview_text,
            text="osu!Tracker",
            bg=PREVIEW_CARD_BG,
            fg="#FFFFFF",
            font=("Comfortaa", 11, "bold"),
            anchor="w",
        ).grid(column=0, row=0, sticky="w")

        tk.Label(
            preview_text,
            textvariable=self.preview_details,
            bg=PREVIEW_CARD_BG,
            fg="#FFFFFF",
            font=("Comfortaa", 9),
            anchor="w",
            justify="left",
            wraplength=450,
        ).grid(column=0, row=1, sticky="w", pady=(5, 0))

        tk.Label(
            preview_text,
            textvariable=self.preview_state,
            bg=PREVIEW_CARD_BG,
            fg=PREVIEW_SUBTLE_TEXT,
            font=("Comfortaa", 9),
            anchor="w",
            justify="left",
            wraplength=450,
        ).grid(column=0, row=2, sticky="w", pady=(2, 0))

        tk.Label(
            preview_text,
            textvariable=self.preview_elapsed,
            bg=PREVIEW_CARD_BG,
            fg=PREVIEW_ELAPSED_TEXT,
            font=("Comfortaa", 9),
            anchor="w",
        ).grid(column=0, row=3, sticky="w", pady=(4, 0))

        tk.Label(
            activity,
            textvariable=self.preview_status_text,
            bg=self.cget("bg"),
            fg=PREVIEW_MUTED_TEXT,
            font=("Comfortaa", 9),
            anchor="w",
            justify="left",
        ).grid(column=0, row=1, sticky="w", pady=(8, 0))

        footer = ttk.Frame(container)
        footer.grid(column=0, row=4, columnspan=3, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.update_status, style="Footer.TLabel").grid(
            column=0, row=0, sticky="w"
        )
        self.github_link_button = ttk.Button(
            footer,
            text="GitHub",
            command=self._open_releases_page,
            style=LINK_BUTTON_STYLE,
            cursor="hand2",
        )
        self.github_link_button.grid(column=1, row=0, sticky="e")
        self.check_update_button = ttk.Button(
            footer,
            text="Check for updates",
            command=self._check_for_update,
            style=LINK_BUTTON_STYLE,
        )
        self.check_update_button.grid(column=2, row=0, sticky="e", padx=(10, 0))
        self.update_button = ttk.Button(
            footer,
            text="Update now",
            command=self._start_update,
            state="disabled",
            style=LINK_BUTTON_STYLE,
        )
        self.update_button.grid(column=3, row=0, sticky="e", padx=(10, 0))

    @staticmethod
    def _discord_option_name(value: str) -> str:
        return next(
            (name for name, option in DISCORD_TEXT_OPTIONS.items() if option == value),
            next(iter(DISCORD_TEXT_OPTIONS)),
        )

    @staticmethod
    def _discord_dropdown(
        parent: ttk.LabelFrame, row: int, label: str, variable: tk.StringVar
    ) -> None:
        ttk.Label(parent, text=f"{label}:").grid(
            column=0, row=row, sticky="w", padx=(0, 12), pady=3
        )
        ttk.Combobox(
            parent,
            textvariable=variable,
            values=list(DISCORD_TEXT_OPTIONS),
            state="readonly",
        ).grid(column=1, row=row, sticky="ew", pady=3)

    @staticmethod
    def _setting_row(
        parent: ttk.LabelFrame, row: int, label: str, variable: tk.StringVar
    ) -> None:
        ttk.Label(parent, text=f"{label}:").grid(
            column=0, row=row, sticky="w", padx=(0, 12), pady=3
        )
        ttk.Entry(parent, textvariable=variable).grid(
            column=1, row=row, sticky="ew", pady=3
        )

    def _read_settings(self) -> Settings | None:
        try:
            interval = float(self.interval.get())
        except ValueError:
            messagebox.showerror(
                "Invalid interval",
                "Update interval must be a number greater than zero.",
            )
            return None
        if interval <= 0:
            messagebox.showerror(
                "Invalid interval", "Update interval must be greater than zero."
            )
            return None

        endpoint = self.endpoint.get().strip()
        if not endpoint:
            messagebox.showerror("Missing endpoint", "Enter a Tosu API endpoint.")
            return None
        return Settings(
            endpoint=endpoint,
            client_id=self.client_id.get().strip() or None,
            interval=interval,
            discord_details=DISCORD_TEXT_OPTIONS[self.discord_details.get()],
            discord_state=DISCORD_TEXT_OPTIONS[self.discord_state.get()],
        )

    def _save(self) -> bool:
        settings = self._read_settings()
        if settings is None:
            return False
        try:
            save_settings(settings, self.settings_path)
        except OSError as error:
            messagebox.showerror("Unable to save settings", str(error))
            return False
        self.status.set("Settings saved.")
        return True

    def _start(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        if not self._save():
            return
        settings = self._read_settings()
        if settings is None:
            return

        self.stop_event.clear()
        self.worker = threading.Thread(
            target=self._track, args=(settings,), daemon=True
        )
        self.worker.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.set("Connecting to Tosu…")

    @staticmethod
    def _open_releases_page() -> None:
        webbrowser.open(RELEASES_PAGE)

    def _check_for_update_background(self) -> None:
        self._check_for_update(manual=False)

    def _check_for_update(self, manual: bool = True) -> None:
        self.check_update_button.configure(state="disabled")
        self.update_button.configure(state="disabled")
        if manual:
            self.status.set("Checking GitHub for updates…")
        thread = threading.Thread(
            target=self._check_for_update_worker,
            args=(manual,),
            daemon=True,
        )
        thread.start()

    def _check_for_update_worker(self, manual: bool) -> None:
        try:
            release = fetch_latest_release()
        except requests.RequestException as error:
            self.events.put(
                ("update-error", (f"Unable to check updates: {error}", manual))
            )
            return
        except ValueError as error:
            self.events.put(
                ("update-error", (f"Invalid update response: {error}", manual))
            )
            return
        self.events.put(("update-info", (release, manual)))

    def _start_update(self) -> None:
        if not self.latest_release_version:
            messagebox.showinfo(
                "No update selected", "Check for updates before updating."
            )
            return

        if not self.latest_release_url:
            messagebox.showinfo(
                "Manual update",
                "No downloadable .exe was found in the latest release. "
                "Opening the releases page.",
            )
            webbrowser.open(RELEASES_PAGE)
            return

        if not getattr(sys, "frozen", False):
            messagebox.showinfo(
                "Manual update",
                "Self-update is available only in the packaged .exe build. "
                "Opening the releases page.",
            )
            webbrowser.open(RELEASES_PAGE)
            return

        if not messagebox.askyesno(
            "Install update",
            f"Install v{self.latest_release_version} now? "
            "The app will close and restart after download.",
        ):
            return

        self.check_update_button.configure(state="disabled")
        self.update_button.configure(state="disabled")
        self.status.set(f"Downloading v{self.latest_release_version}…")
        thread = threading.Thread(target=self._start_update_worker, daemon=True)
        thread.start()

    def _start_update_worker(self) -> None:
        if not self.latest_release_url:
            self.events.put(("update-error", ("No release download URL found.", True)))
            return
        try:
            begin_windows_self_update(self.latest_release_url)
        except requests.RequestException as error:
            self.events.put(("update-error", (f"Download failed: {error}", True)))
            return
        except OSError as error:
            self.events.put(("update-error", (f"Update failed: {error}", True)))
            return
        self.events.put(("update-started", None))

    def _stop(self) -> None:
        self.stop_event.set()
        self.status.set("Stopping tracker…")

    def _track(self, settings: Settings) -> None:
        rpc = DiscordRPC(
            settings.client_id,
            settings.discord_details,
            settings.discord_state,
        )
        discord_connected = rpc.connect()
        self.events.put(
            (
                "status",
                "Tracking Tosu" + (" and Discord." if discord_connected else "."),
            )
        )
        try:
            while not self.stop_event.is_set():
                try:
                    model = fetch_tosu_data(settings.endpoint)
                except requests.RequestException as error:
                    self.events.put(("error", f"Unable to connect to Tosu: {error}"))
                except ValueError as error:
                    self.events.put(("error", f"Unable to read Tosu data: {error}"))
                else:
                    rpc.update(model)
                    self.events.put(("model", model))
                self.stop_event.wait(settings.interval)
        finally:
            rpc.close()
            self.events.put(("stopped", None))

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                self._handle_event(event, value)
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _handle_event(self, event: str, value: object) -> None:
        if event in {"status", "error"}:
            self.status.set(str(value))
            return
        if event == "model":
            self._display_model(value)
            return
        if event == "stopped":
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.status.set("Tracker stopped.")
            return
        if event == "update-error":
            self._handle_update_error(value)
            return
        if event == "update-info":
            self._handle_update_info(value)
            return
        if event == "update-started":
            messagebox.showinfo(
                "Updating",
                "Update downloaded. The app will now restart.",
            )
            self._close()

    def _handle_update_error(self, value: object) -> None:
        if not isinstance(value, tuple) or len(value) != 2:
            return
        message, manual = value
        self.check_update_button.configure(state="normal")
        self.latest_release_version = None
        self.latest_release_url = None
        self.update_button.configure(state="disabled")
        if bool(manual):
            self.status.set(str(message))

    def _handle_update_info(self, value: object) -> None:
        if not isinstance(value, tuple) or len(value) != 2:
            return
        release, manual = value
        self.check_update_button.configure(state="normal")
        latest = getattr(release, "version", "0.0.0")
        self.latest_release_version = latest
        self.latest_release_url = getattr(release, "exe_download_url", None)
        current = self.current_version
        self.update_status.set(f"Current version: v{current} | Latest: v{latest}")
        if is_update_available(current, latest):
            self.status.set(f"Update available: v{latest}")
            self.update_button.configure(state="normal")
            return
        self.update_button.configure(state="disabled")
        if bool(manual):
            self.status.set("You already have the latest version.")

    def _display_model(self, model: object) -> None:
        if not isinstance(model, Model):
            return

        self.latest_model = model

        details_field = DISCORD_TEXT_OPTIONS.get(
            self.discord_details.get(), DEFAULT_DISCORD_DETAILS
        )
        state_field = DISCORD_TEXT_OPTIONS.get(
            self.discord_state.get(), DEFAULT_DISCORD_STATE
        )
        activity_state = self._preview_activity_state(model)

        self.preview_activity.set(activity_state)
        details = DiscordRPC._text_value(model, details_field, activity_state)[:128]
        state = DiscordRPC._text_value(model, state_field, activity_state)[:128]
        self.preview_details.set(details)
        self.preview_state.set(state)

        if model.menu.state == 2:
            large_image_url, large_text, _ = DiscordRPC._beatmap_art(model)
        else:
            large_image_url, large_text, _ = OSU_LOGO_URL, "osu!", None

        self.preview_large_text.set(large_text[:128])
        self.preview_status_text.set(
            f"Activity: {activity_state}  |  Asset text: {self.preview_large_text.get()}"
        )
        self._set_preview_image(large_image_url)

        elapsed_seconds = max(0, int(model.menu.bm.time.current / 1000))
        minutes, seconds = divmod(elapsed_seconds, 60)
        self.preview_elapsed.set(f"{minutes:02d}:{seconds:02d} elapsed")

    def _preview_activity_state(self, model: Model) -> str:
        """Mirror DiscordRPC state logic so the preview matches the posted activity."""
        return self.preview_state_tracker._activity_state(model)

    def _refresh_preview_from_latest_model(self, *_: object) -> None:
        if self.latest_model is not None:
            self._display_model(self.latest_model)

    def _set_preview_image(self, image_url: str) -> None:
        if self.preview_image_label is None:
            return

        preview_image = self._load_preview_image(image_url, (72, 72))
        if preview_image is None:
            self.preview_image_label.configure(
                image="", textvariable=self.preview_fallback_icon
            )
            self.preview_image_label.image = None
            self.preview_current_image_url = None
            return

        self.preview_image_label.configure(image=preview_image, text="")
        self.preview_image_label.image = preview_image
        self.preview_current_image_url = image_url

    def _load_preview_image(
        self, image_url: str, size: tuple[int, int]
    ) -> object | None:
        if not image_url:
            return None

        cached = self.preview_image_cache.get(image_url)
        if cached is not None:
            return cached

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

        self.preview_image_cache[image_url] = preview_image
        if len(self.preview_image_cache) > 12:
            # Keep cache bounded; most sessions only need a few recent maps.
            self.preview_image_cache = dict(list(self.preview_image_cache.items())[-8:])
        return preview_image

    def _close(self) -> None:
        self.stop_event.set()
        self.destroy()


def launch(settings: Settings, settings_path: Path) -> None:
    """Open the desktop tracker window."""
    app = TrackerApp(settings, settings_path)
    app.mainloop()


def main() -> None:
    """Load the saved settings and open the desktop application."""
    settings_path = default_settings_path()
    launch(load_settings(settings_path), settings_path)
