"""Import page: scan a parent folder and add the sub-folders that look like projects."""
from __future__ import annotations

import os
from tkinter import filedialog

import customtkinter as ctk

from core import tech_detector
from core.models import FolderCandidate
from core.validators import STATUSES
from ui import theme
from ui.pages.base import Page
from ui.widgets import controls
from ui.widgets.badge import Badge
from ui.widgets.empty_state import EmptyState
from ui.widgets.spinner import Spinner
from ui.widgets.text_field import TextField


class ImportPage(Page):
    key = "import"
    title = "Import projects"
    subtitle = "Add a whole folder of projects at once"

    def __init__(self, master, window):
        super().__init__(master, window)
        self.parent_folder = ""
        self.candidates: list[FolderCandidate] = []
        self.checks: dict[str, ctk.BooleanVar] = {}
        self._build()

    def _build(self) -> None:
        top = controls.card(self)
        top.pack(fill="x", padx=theme.XL, pady=(theme.LG, theme.MD))
        inner = controls.transparent(top)
        inner.pack(fill="x", padx=theme.XL, pady=theme.LG)
        controls.label(inner, "Choose a parent folder", "subtitle", "bold").pack(anchor="w")
        controls.label(inner, "DevDock lists its sub-folders that look like projects (Python, Node, Java, C#, "
                              "Flutter, Power BI, Jupyter or any git repository).", "caption", color="muted",
                       wraplength=760).pack(anchor="w", pady=(0, theme.MD))
        row = controls.transparent(inner)
        row.pack(fill="x")
        self.path_entry = TextField(row, r"C:\Users\you\Projects")
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.path_entry.bind("<Return>", lambda _e: self.scan(self.path_entry.value))
        controls.button(row, "Browse…", self.browse, "primary", icon="folder").pack(side="left", padx=(theme.SM, 0))
        controls.button(row, "Scan", lambda: self.scan(self.path_entry.value), "secondary",
                        icon="search").pack(side="left", padx=(theme.SM, 0))

        self.bar = controls.transparent(self)
        self.bar.pack(fill="x", padx=theme.XL, pady=(0, theme.SM))
        self.all_var = ctk.BooleanVar(value=True)
        self.all_check = ctk.CTkCheckBox(self.bar, text="Select all", variable=self.all_var, command=self._toggle_all,
                                         font=theme.font("body"))
        self.count_label = controls.label(self.bar, "", "caption", color="muted")
        self.add_btn = controls.button(self.bar, "Add selected", self.add_selected, "primary", icon="plus")
        self.status_menu = controls.option_menu(self.bar, STATUSES, width=130)
        self.status_menu.set(self.ctx.settings.default_status)
        self.status_caption = controls.label(self.bar, "Status for new projects", "caption", color="muted")

        self.list = controls.scroll_frame(self)
        self.list.pack(fill="both", expand=True, padx=theme.LG, pady=(0, theme.SM))
        self._show_intro()

    def _show_intro(self) -> None:
        self._clear_list()
        self._show_bar(False)
        EmptyState(self.list, "import", "Nothing scanned yet",
                   "Pick the folder that holds your projects, for example C:\\Users\\you\\Projects.",
                   ).pack(pady=theme.LG)

    def _clear_list(self) -> None:
        for child in self.list.winfo_children():
            child.destroy()

    def _show_bar(self, visible: bool) -> None:
        for widget in (self.all_check, self.count_label, self.add_btn, self.status_menu, self.status_caption):
            widget.pack_forget()
        if visible:
            self.all_check.pack(side="left")
            self.count_label.pack(side="left", padx=theme.LG)
            self.add_btn.pack(side="right")
            self.status_menu.pack(side="right", padx=(0, theme.MD))
            self.status_caption.pack(side="right", padx=(0, theme.SM))

    # ------------------------------------------------------------------ scanning
    def browse(self) -> None:
        start = self.parent_folder if os.path.isdir(self.parent_folder) else os.path.expanduser("~")
        folder = filedialog.askdirectory(parent=self.window, title="Choose the folder that contains your projects",
                                         initialdir=start, mustexist=True)
        if folder:
            self.scan(folder)

    def scan(self, folder: str) -> None:
        folder = os.path.normpath(folder.strip().strip('"')) if folder.strip() else ""
        if not folder or not os.path.isdir(folder):
            self.window.toasts.show("Choose a folder that exists.", "warning")
            return
        self.parent_folder = folder
        self.path_entry.set_value(folder)
        self._clear_list()
        self._show_bar(False)
        Spinner(self.list, f"Scanning {folder}…", "body").start().pack(anchor="w", padx=theme.MD, pady=theme.LG)
        registered = self.ctx.projects.registered_folders()
        self.window.runner.submit(tech_detector.scan_parent, folder, registered, on_success=self._scanned,
                                  on_error=self._scan_failed, owner=self)

    def _scan_failed(self, error: BaseException) -> None:
        self._clear_list()
        self.window.toasts.show(f"Could not scan the folder: {error}", "error")

    def _scanned(self, candidates: list[FolderCandidate]) -> None:
        self.candidates = candidates
        self.checks = {}
        self._clear_list()
        if not candidates:
            EmptyState(self.list, "search", "No projects found",
                       "None of the sub-folders look like a project. Try a different folder, or add a project "
                       "manually.", "Add project", lambda: self.window.navigate("form")).pack(pady=theme.LG)
            return
        for candidate in candidates:
            self._row(candidate)
        self._show_bar(True)
        self.all_var.set(True)
        self._update_count()

    def _row(self, candidate: FolderCandidate) -> None:
        row = controls.card(self.list, corner_radius=theme.RADIUS_INPUT)
        row.pack(fill="x", padx=theme.SM, pady=3)
        var = ctk.BooleanVar(value=not candidate.already_added)
        check = ctk.CTkCheckBox(row, text="", variable=var, width=24, command=self._update_count,
                                state="disabled" if candidate.already_added else "normal")
        check.pack(side="left", padx=(theme.MD, theme.SM), pady=theme.MD)
        if not candidate.already_added:
            self.checks[candidate.path] = var
        # Badges are packed before the text so a long path can never push them out of view.
        if candidate.already_added:
            Badge(row, "Already added", "muted").pack(side="right", padx=theme.MD)
        Badge(row, candidate.technology, "accent").pack(side="right", padx=(0, theme.SM) if candidate.already_added
                                                         else theme.MD)
        text = controls.transparent(row)
        text.pack(side="left", fill="x", expand=True, pady=theme.SM)
        controls.label(text, candidate.name, "body", "bold").pack(anchor="w")
        controls.label(text, candidate.path, "caption", color="muted").pack(anchor="w")

    def _toggle_all(self) -> None:
        for var in self.checks.values():
            var.set(self.all_var.get())
        self._update_count()

    def _selected(self) -> list[FolderCandidate]:
        return [c for c in self.candidates if c.path in self.checks and self.checks[c.path].get()]

    def _update_count(self) -> None:
        selected = len(self._selected())
        available = len(self.checks)
        skipped = len(self.candidates) - available
        text = f"{selected} of {available} selected"
        if skipped:
            text += f"  ·  {skipped} already in DevDock"
        self.count_label.configure(text=text)
        self.add_btn.configure(text=f"Add selected ({selected})" if selected else "Add selected",
                               state="normal" if selected else "disabled")

    def add_selected(self) -> None:
        chosen = self._selected()
        if not chosen:
            return
        result = self.ctx.projects.add_many(chosen, self.status_menu.get())
        message = f"Added {result.added} project{'s' if result.added != 1 else ''}"
        if result.skipped:
            message += f", skipped {result.skipped}"
        self.window.toasts.show(message, "success" if result.added else "info")
        if result.errors:
            self.window.toasts.show("; ".join(result.errors[:3]), "warning")
        self.window.notify_data_changed()
        self.window.refresh_missing()
        self.scan(self.parent_folder)

    def handle_key(self, action: str) -> bool:
        if action == "enter" and self._selected():
            self.add_selected()
            return True
        return False
