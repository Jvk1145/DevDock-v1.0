"""Responsive grid: 2–4 columns depending on the available width (1 column in list view)."""
from __future__ import annotations

import customtkinter as ctk

from ui import theme


def columns_for(width_px: int, scale: float, min_col: int = 400, min_cols: int = 2, max_cols: int = 4) -> int:
    logical = width_px / (scale or 1.0)
    return max(min_cols, min(max_cols, int(logical // min_col)))


class CardGrid(ctk.CTkFrame):
    def __init__(self, master, min_col_width: int = 400, min_cols: int = 2, max_cols: int = 4):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.min_col_width = min_col_width
        self.min_cols = min_cols
        self.max_cols = max_cols
        self.layout = "grid"
        self.cards: list[ctk.CTkBaseClass] = []
        self.columns = min_cols
        self._configured_columns = 0
        self.bind("<Configure>", self._on_configure, add="+")

    def set_cards(self, cards: list, layout: str = "grid") -> None:
        for card in self.cards:
            if card not in cards:
                try:
                    card.grid_remove()
                except Exception:
                    pass
        self.cards = list(cards)
        self.layout = layout
        self._relayout(force=True)

    def _target_columns(self) -> int:
        if self.layout != "grid":
            return 1
        width = self.winfo_width()
        if width <= 1:
            width = self.master.winfo_width()
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        return columns_for(width, scale, self.min_col_width, self.min_cols, self.max_cols)

    def _on_configure(self, event) -> None:
        # CTkFrame.bind() binds its internal canvas, so the event comes from that canvas.
        if event.widget in (self, self._canvas) and self._target_columns() != self.columns:
            self._relayout(force=True)

    def _relayout(self, force: bool = False) -> None:
        columns = self._target_columns()
        if not force and columns == self.columns:
            return
        self.columns = columns
        for index in range(max(self._configured_columns, columns)):
            if index < columns:
                self.grid_columnconfigure(index, weight=1, uniform="card")
            else:
                self.grid_columnconfigure(index, weight=0, uniform="")
        self._configured_columns = columns
        gap = theme.MD // 2
        for index, card in enumerate(self.cards):
            card.grid(row=index // columns, column=index % columns, sticky="nsew", padx=gap, pady=gap)
