"""Desktop interface for osu!Tracker."""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import requests

from OsuTracker.discord_rpc import DiscordRPC
from OsuTracker.models.tosu import Model
from OsuTracker.settings import (
    DISCORD_TEXT_OPTIONS,
    Settings,
    default_settings_path,
    load_settings,
    save_settings,
)
from OsuTracker.tosu import fetch_tosu_data


class TrackerApp(tk.Tk):
    """A small desktop app for configuring and running the tracker."""

    def __init__(self, settings: Settings, settings_path: Path) -> None:
        super().__init__()
        self.title("osu!Tracker")
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
        self.map_text = tk.StringVar(value="No beatmap detected")
        self.details = {
            "State": tk.StringVar(value="—"),
            "Difficulty": tk.StringVar(value="—"),
            "Mods": tk.StringVar(value="—"),
            "Accuracy": tk.StringVar(value="—"),
            "PP": tk.StringVar(value="—"),
            "Combo": tk.StringVar(value="—"),
            "Progress": tk.StringVar(value="—"),
        }

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._process_events)

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="osu!Tracker", font=("Segoe UI", 18, "bold")).grid(
            column=0, row=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            container,
            text="Live beatmap stats and Discord Rich Presence",
        ).grid(column=0, row=1, columnspan=3, sticky="w", pady=(0, 12))

        settings_frame = ttk.LabelFrame(container, text="Settings", padding=12)
        settings_frame.grid(column=0, row=2, columnspan=3, sticky="ew")
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
        buttons.grid(column=0, row=3, columnspan=3, sticky="ew", pady=12)
        ttk.Button(buttons, text="Save settings", command=self._save).pack(side="left")
        self.start_button = ttk.Button(
            buttons, text="Start tracking", command=self._start
        )
        self.start_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            buttons, text="Stop", command=self._stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        ttk.Label(container, textvariable=self.status, foreground="#267a36").grid(
            column=0, row=4, columnspan=3, sticky="w", pady=(0, 12)
        )

        activity = ttk.LabelFrame(container, text="Current activity", padding=12)
        activity.grid(column=0, row=5, columnspan=3, sticky="nsew")
        activity.columnconfigure(1, weight=1)
        ttk.Label(
            activity,
            textvariable=self.map_text,
            font=("Segoe UI", 12, "bold"),
            wraplength=570,
        ).grid(column=0, row=0, columnspan=2, sticky="w", pady=(0, 8))
        for row, (label, variable) in enumerate(self.details.items(), start=1):
            ttk.Label(activity, text=f"{label}:").grid(
                column=0, row=row, sticky="nw", padx=(0, 12), pady=2
            )
            ttk.Label(activity, textvariable=variable, wraplength=480).grid(
                column=1, row=row, sticky="nw", pady=2
            )

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
                if event == "status":
                    self.status.set(str(value))
                elif event == "error":
                    self.status.set(str(value))
                elif event == "model":
                    self._display_model(value)
                elif event == "stopped":
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.status.set("Tracker stopped.")
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _display_model(self, model: object) -> None:
        if not isinstance(model, Model):
            return
        metadata = model.menu.bm.metadata
        self.map_text.set(f"{metadata.artist} - {metadata.title}")
        self.details["State"].set(
            "Playing" if model.menu.state == 2 else "Browsing songs"
        )
        self.details["Difficulty"].set(
            f"{metadata.difficulty} · {model.menu.bm.stats.fullSR:.2f}★"
        )
        self.details["Mods"].set(model.menu.mods.str or "NoMod")
        self.details["Accuracy"].set(f"{model.gameplay.accuracy:.2f}%")
        self.details["PP"].set(
            f"{model.gameplay.pp.current:.0f} / {model.gameplay.pp.maxThisPlay:.0f} pp"
        )
        self.details["Combo"].set(
            f"{model.gameplay.combo.current}x / {model.gameplay.combo.max}x"
        )
        full_time = model.menu.bm.time.full
        progress = (
            0 if full_time <= 0 else round(model.menu.bm.time.current / full_time * 100)
        )
        self.details["Progress"].set(f"{min(100, max(0, progress))}%")

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
