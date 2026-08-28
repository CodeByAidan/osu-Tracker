"""Desktop interface for osu!Tracker."""

import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from ctypes import windll
from pathlib import Path
from tkinter import messagebox, ttk

from OsuTracker.discord_rpc import DiscordRPC
from OsuTracker.gui_components.preview import RichPresencePreview
from OsuTracker.gui_components.settings_form import SettingsForm
from OsuTracker.gui_components.tracker_controls import TrackerControls
from OsuTracker.gui_components.update_panel import UpdatePanel
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
from OsuTracker.services.tracker_service import track
from OsuTracker.services.update_service import check_for_update, download_update
from OsuTracker.updater import RELEASES_PAGE, current_version

LINK_BUTTON_STYLE = "Link.TButton"


def _load_font(font_path: Path) -> None:
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
        _load_font(resource_root / "assets" / "fonts" / "Comfortaa[wght].ttf")
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
            self.iconbitmap(str(resource_root / "images" / "osu-tracker.ico"))  # type: ignore
        except tk.TclError:
            pass
        self.minsize(660, 560)
        self._initial_settings = settings
        self.settings_path = settings_path
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None

        self.settings_form: SettingsForm | None = None
        self.status = tk.StringVar(
            value="Ready. Configure settings, then start tracking."
        )
        self.error_panel: ttk.Frame | None = None
        self.error_text: tk.Text | None = None
        self.current_version = current_version()
        self.preview_state_tracker = DiscordRPC(settings.client_id)
        self.preview: RichPresencePreview | None = None
        self.controls: TrackerControls | None = None
        self.update_panel: UpdatePanel | None = None
        self.latest_model: Model | None = None

        self._build()
        assert self.settings_form is not None
        self.settings_form.details_variable.trace_add(
            "write", self._refresh_preview_from_latest_model
        )
        self.settings_form.state_variable.trace_add(
            "write", self._refresh_preview_from_latest_model
        )
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._process_events)
        self.after(800, self._check_for_update_background)

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.grid(sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        self.settings_form = SettingsForm(
            container, self._initial_settings, self.settings_path
        )
        self.settings_form.grid(column=0, row=0, columnspan=3, sticky="ew")

        self.controls = TrackerControls(
            container,
            self._save,
            self._start,
            self._stop,
        )
        self.controls.grid(column=0, row=1, columnspan=3, sticky="ew", pady=12)
        ttk.Label(container, textvariable=self.status, style="Status.TLabel").grid(
            column=0, row=2, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.error_panel = ttk.Frame(container)
        self.error_panel.columnconfigure(0, weight=1)
        self.error_text = tk.Text(
            self.error_panel,
            height=6,
            width=1,
            wrap=tk.WORD,
            state="disabled",
            takefocus=False,
            bg="#2b2b2b",
            fg="#ff66aa",
            insertbackground="#ff66aa",
            relief="flat",
            padx=4,
            pady=4,
        )
        error_scrollbar = ttk.Scrollbar(
            self.error_panel,
            orient="vertical",
            command=lambda *args: self.error_text.yview(*args)
            if self.error_text is not None
            else None,
        )
        self.error_text.configure(yscrollcommand=error_scrollbar.set)
        self.error_text.grid(column=0, row=0, sticky="nsew")
        error_scrollbar.grid(column=1, row=0, sticky="ns")
        self.error_panel.grid(column=0, row=3, columnspan=3, sticky="nsew")
        self.error_panel.grid_remove()

        self.preview = RichPresencePreview(container, self.preview_state_tracker)
        self.preview.grid(column=0, row=4, columnspan=3, sticky="nsew")
        container.rowconfigure(4, weight=1)

        self.update_panel = UpdatePanel(
            container,
            self.current_version,
            self._open_releases_page,
            self._check_for_update,
            self._start_update,
        )
        self.update_panel.grid(column=0, row=5, columnspan=3, sticky="ew", pady=(10, 0))

    def _read_settings(self) -> Settings | None:
        return self.settings_form.read() if self.settings_form is not None else None

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
            target=track, args=(settings, self.stop_event, self.events), daemon=True
        )
        self.worker.start()
        if self.controls is not None:
            self.controls.show_running()
        self.status.set("Connecting to Tosu…")

    @staticmethod
    def _open_releases_page() -> None:
        webbrowser.open(RELEASES_PAGE)

    def _check_for_update_background(self) -> None:
        self._check_for_update(manual=False)

    def _check_for_update(self, manual: bool = True) -> None:
        if self.update_panel is None:
            return
        self.update_panel.show_checking()
        if manual:
            self.status.set("Checking GitHub for updates…")
        thread = threading.Thread(
            target=check_for_update,
            args=(manual, self.events),
            daemon=True,
        )
        thread.start()

    def _start_update(self) -> None:
        if self.update_panel is None or not self.update_panel.latest_release_version:
            messagebox.showinfo(
                "No update selected", "Check for updates before updating."
            )
            return

        if not self.update_panel.latest_release_url:
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
            f"Install v{self.update_panel.latest_release_version} now? "
            "The app will close and restart after download.",
        ):
            return

        self.update_panel.show_downloading()
        self.status.set(f"Downloading v{self.update_panel.latest_release_version}…")
        thread = threading.Thread(
            target=download_update,
            args=(self.update_panel.latest_release_url, self.events),
            daemon=True,
        )
        thread.start()

    def _stop(self) -> None:
        self.stop_event.set()
        self.status.set("Stopping tracker…")

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                self._handle_event(event, value)
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _handle_event(self, event: str, value: object) -> None:
        if event == "status":
            self.status.set(str(value))
            return
        if event == "error":
            self.status.set("Error details (scroll to read).")
            self._show_error(value)
            return
        if event == "model":
            self._hide_error()
            self._display_model(value)
            return
        if event == "stopped":
            if self.controls is not None:
                self.controls.show_stopped()
            self.status.set("Tracker stopped.")
            return
        if event == "update-error":
            self._handle_update_error(value)
            return
        if event == "update-info":
            self._handle_update_info(value)
            return
        if event == "update-progress":
            self._handle_update_progress(value)
            return
        if event == "update-started":
            if self.update_panel is not None:
                self.update_panel.show_started()
            messagebox.showinfo(
                "Updating",
                f"Update downloaded. The app will now restart.\n\n"
                f"Update log:\n{value}",
            )
            self._close()

    def _handle_update_progress(self, value: object) -> None:
        if self.update_panel is not None:
            status = self.update_panel.show_progress(value)
            if status:
                self.status.set(status)

    def _handle_update_error(self, value: object) -> None:
        if self.update_panel is not None:
            status = self.update_panel.show_error(value)
            if status:
                self.status.set(status)
                self._show_error(status)

    def _show_error(self, value: object) -> None:
        if self.error_panel is None or self.error_text is None:
            return
        self.error_text.configure(state="normal")
        self.error_text.delete("1.0", tk.END)
        self.error_text.insert("1.0", str(value))
        self.error_text.configure(state="disabled")
        self.error_text.see("1.0")
        self.error_panel.grid()

    def _hide_error(self) -> None:
        if self.error_panel is not None:
            self.error_panel.grid_remove()

    def _handle_update_info(self, value: object) -> None:
        if self.update_panel is not None:
            status = self.update_panel.show_release(value)
            if status:
                self.status.set(status)

    def _display_model(self, model: object) -> None:
        if (
            not isinstance(model, Model)
            or self.preview is None
            or self.settings_form is None
        ):
            return

        self.latest_model = model

        details_field = DISCORD_TEXT_OPTIONS.get(
            self.settings_form.details_variable.get(), DEFAULT_DISCORD_DETAILS
        )
        state_field = DISCORD_TEXT_OPTIONS.get(
            self.settings_form.state_variable.get(), DEFAULT_DISCORD_STATE
        )
        self.preview.display(model, details_field, state_field)

    def _refresh_preview_from_latest_model(self, *_: object) -> None:
        if self.latest_model is not None:
            self._display_model(self.latest_model)

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
