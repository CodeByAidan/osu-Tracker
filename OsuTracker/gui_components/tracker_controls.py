"""Tracker action controls for the desktop application."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class TrackerControls(ttk.Frame):
    """Expose save, start, and stop actions with consistent button state."""

    def __init__(
        self,
        parent: tk.Misc,
        on_save: Callable[[], bool],
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        ttk.Button(self, text="Save settings", command=on_save).pack(side="left")
        self.start_button = ttk.Button(self, text="Start tracking", command=on_start)
        self.start_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            self, text="Stop", command=on_stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))

    def show_running(self) -> None:
        """Disable starting and enable stopping while tracking is active."""
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def show_stopped(self) -> None:
        """Enable starting and disable stopping after tracking ends."""
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
