"""Settings form widget for the desktop tracker."""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from OsuTracker.settings import DISCORD_TEXT_OPTIONS, Settings


class SettingsForm(ttk.LabelFrame):
    """Edit and validate the settings used by the tracker."""

    def __init__(
        self, parent: tk.Misc, settings: Settings, settings_path: Path
    ) -> None:
        super().__init__(parent, text="Settings", padding=12)
        self._endpoint = tk.StringVar(self, value=settings.endpoint)
        self._client_id = tk.StringVar(self, value=settings.client_id or "")
        self._interval = tk.StringVar(self, value=f"{settings.interval:g}")
        self._details = tk.StringVar(
            self, value=self._option_name(settings.discord_details)
        )
        self._state = tk.StringVar(
            self, value=self._option_name(settings.discord_state)
        )
        self._build(settings_path)

    @property
    def details_variable(self) -> tk.StringVar:
        """Return the variable backing the Discord Details selection."""
        return self._details

    @property
    def state_variable(self) -> tk.StringVar:
        """Return the variable backing the Discord State selection."""
        return self._state

    def read(self) -> Settings | None:
        """Return validated settings, showing an error for invalid form input."""
        try:
            interval = float(self._interval.get())
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

        endpoint = self._endpoint.get().strip()
        if not endpoint:
            messagebox.showerror("Missing endpoint", "Enter a Tosu API endpoint.")
            return None
        return Settings(
            endpoint=endpoint,
            client_id=self._client_id.get().strip() or None,
            interval=interval,
            discord_details=DISCORD_TEXT_OPTIONS[self._details.get()],
            discord_state=DISCORD_TEXT_OPTIONS[self._state.get()],
        )

    def _build(self, settings_path: Path) -> None:
        self.columnconfigure(1, weight=1)
        self._setting_row(0, "Tosu API endpoint", self._endpoint)
        self._setting_row(1, "Discord application ID", self._client_id)
        self._setting_row(2, "Update interval (seconds)", self._interval)
        self._discord_dropdown(3, "Discord Details", self._details)
        self._discord_dropdown(4, "Discord State", self._state)
        ttk.Label(
            self,
            text=f"Saved locally: {settings_path}",
            wraplength=590,
        ).grid(column=0, row=5, columnspan=2, sticky="w", pady=(8, 0))

    def _setting_row(self, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(self, text=f"{label}:").grid(
            column=0, row=row, sticky="w", padx=(0, 12), pady=3
        )
        ttk.Entry(self, textvariable=variable).grid(
            column=1, row=row, sticky="ew", pady=3
        )

    def _discord_dropdown(self, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(self, text=f"{label}:").grid(
            column=0, row=row, sticky="w", padx=(0, 12), pady=3
        )
        ttk.Combobox(
            self,
            textvariable=variable,
            values=list(DISCORD_TEXT_OPTIONS),
            state="readonly",
        ).grid(column=1, row=row, sticky="ew", pady=3)

    @staticmethod
    def _option_name(value: str) -> str:
        return next(
            (name for name, option in DISCORD_TEXT_OPTIONS.items() if option == value),
            next(iter(DISCORD_TEXT_OPTIONS)),
        )
