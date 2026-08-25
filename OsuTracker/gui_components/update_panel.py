"""Update controls and progress display for the desktop tracker."""

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from OsuTracker.updater import is_update_available

LINK_BUTTON_STYLE = "Link.TButton"


class UpdatePanel(ttk.Frame):
    """Display update status and expose update actions to the main window."""

    def __init__(
        self,
        parent: tk.Misc,
        current_version: str,
        on_open_releases: Callable[[], None],
        on_check: Callable[[], None],
        on_update: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._current_version = current_version
        self.latest_release_version: str | None = None
        self.latest_release_url: str | None = None
        self.status = tk.StringVar(self, value=f"Current version: v{current_version}")
        self.progress = ttk.Progressbar(self, mode="determinate", length=120)
        self.check_button = ttk.Button(
            self, text="Check for updates", command=on_check, style=LINK_BUTTON_STYLE
        )
        self.update_button = ttk.Button(
            self,
            text="Update now",
            command=on_update,
            state="disabled",
            style=LINK_BUTTON_STYLE,
        )
        self._build(on_open_releases)

    def show_checking(self) -> None:
        """Disable update actions while a release check is running."""
        self.check_button.configure(state="disabled")
        self.update_button.configure(state="disabled")

    def show_downloading(self) -> None:
        """Reset the progress indicator before downloading an update."""
        self.check_button.configure(state="disabled")
        self.update_button.configure(state="disabled")
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)

    def show_progress(self, value: object) -> str | None:
        """Render a download progress event and return if its shape is invalid."""
        if not isinstance(value, tuple) or len(value) != 2:
            return None
        downloaded, total = value
        if not isinstance(downloaded, int):
            return None
        if isinstance(total, int) and total > 0:
            self.progress.stop()
            self.progress.configure(mode="determinate", maximum=total, value=downloaded)
            percent = downloaded * 100 // total
            return f"Downloading update… {percent}%"
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)
        return f"Downloading update… {downloaded // 1024} KB"

    def show_error(self, value: object) -> str | None:
        """Reset update controls after an update error."""
        if not isinstance(value, tuple) or len(value) != 2:
            return None
        message, manual = value
        self.check_button.configure(state="normal")
        self.latest_release_version = None
        self.latest_release_url = None
        self.update_button.configure(state="disabled")
        if bool(manual):
            return str(message)
        return None

    def show_release(self, value: object) -> str | None:
        """Render release information and enable installation when appropriate."""
        if not isinstance(value, tuple) or len(value) != 2:
            return None
        release, manual = value
        self.check_button.configure(state="normal")
        latest = getattr(release, "version", "0.0.0")
        self.latest_release_version = latest
        self.latest_release_url = getattr(release, "exe_download_url", None)
        self.status.set(
            f"Current version: v{self._current_version} | Latest: v{latest}"
        )
        if is_update_available(self._current_version, latest):
            self.update_button.configure(state="normal")
            if bool(manual):
                return f"Update available: v{latest}"
            return None
        self.update_button.configure(state="disabled")
        if bool(manual):
            return "You already have the latest version."
        return None

    def show_started(self) -> None:
        """Stop the progress animation after the update helper starts."""
        self.progress.stop()
        self.progress.configure(value=100)

    def _build(self, on_open_releases: Callable[[], None]) -> None:
        self.columnconfigure(0, weight=1)
        ttk.Label(self, textvariable=self.status, style="Footer.TLabel").grid(
            column=0, row=0, sticky="w"
        )
        self.progress.grid(column=1, row=0, sticky="e", padx=(10, 0))
        ttk.Button(
            self,
            text="GitHub",
            command=on_open_releases,
            style=LINK_BUTTON_STYLE,
            cursor="hand2",
        ).grid(column=2, row=0, sticky="e")
        self.check_button.grid(column=3, row=0, sticky="e", padx=(10, 0))
        self.update_button.grid(column=4, row=0, sticky="e", padx=(10, 0))
