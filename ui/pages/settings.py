"""Settings: appearance, IDE paths, defaults and data management."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

import config
from core.errors import DevDockError, LaunchError
from core.ide_detector import DEFINITIONS, IDEDefinition, ide_name
from core.models import IDE
from core.validators import STATUSES, normalize_path
from ui import theme
from ui.pages.base import Page
from ui.widgets import controls
from ui.widgets.dialogs import BackupPickerDialog, MessageDialog, confirm, info
from ui.widgets.icon_button import IconButton
from ui.widgets.spinner import Spinner
from ui.widgets.text_field import TextField

log = logging.getLogger(__name__)

THEME_LABELS = {"dark": "Dark", "light": "Light", "system": "System"}
ASK_LABEL = "Ask every time"


class SettingsPage(Page):
    key = "settings"
    title = "Settings"
    subtitle = "Appearance, IDEs, defaults and data"

    def __init__(self, master, window):
        super().__init__(master, window)
        self.ides: dict[str, IDE] = {}
        self.ide_rows: dict[str, dict] = {}
        self.scroll = controls.scroll_frame(self)
        self.scroll.pack(fill="both", expand=True, padx=theme.LG - theme.XS)
        self.body = controls.transparent(self.scroll)
        self.body.pack(fill="both", expand=True, padx=theme.SM, pady=(theme.LG, theme.XL))
        self._appearance()
        self._ide_section()
        self._defaults()
        self._data()

    def refresh(self) -> None:
        self.dirty = False
        self.detect(refresh=False)
        self._update_backup_label()

    # ------------------------------------------------------------------ appearance
    def _appearance(self) -> None:
        box, body = controls.section(self.body, "Appearance", "Theme and accent colour apply immediately.", "palette")
        box.pack(fill="x", pady=(0, theme.LG))
        row = controls.transparent(body)
        row.pack(fill="x", pady=(0, theme.MD))
        controls.label(row, "Theme", "body", "bold", width=120).pack(side="left")
        self.theme_seg = ctk.CTkSegmentedButton(row, values=list(THEME_LABELS.values()), command=self._set_theme,
                                                font=theme.font("body"), height=theme.CONTROL_HEIGHT)
        self.theme_seg.set(THEME_LABELS[self.ctx.settings.theme])
        self.theme_seg.pack(side="left")

        row = controls.transparent(body)
        row.pack(fill="x")
        controls.label(row, "Accent colour", "body", "bold", width=120).pack(side="left")
        current = theme.accent_name()
        for name, (base, hover) in theme.ACCENTS.items():
            selected = name == current
            swatch = ctk.CTkButton(row, text="✓" if selected else "", width=30, height=30, corner_radius=15,
                                   fg_color=base, hover_color=hover, text_color="#FFFFFF",
                                   border_width=3 if selected else 0, border_color=theme.c("text"),
                                   font=theme.font("body", "bold"), command=lambda n=name: self._set_accent(n))
            swatch.pack(side="left", padx=(0, theme.SM))
        controls.label(row, current, "caption", color="muted").pack(side="left", padx=theme.SM)

    def _set_theme(self, label: str) -> None:
        mode = next(k for k, v in THEME_LABELS.items() if v == label)
        self.ctx.settings.theme = mode
        theme.apply_mode(mode)
        self.window.toasts.show(f"{label} theme applied", "info")

    def _set_accent(self, name: str) -> None:
        if name == theme.accent_name():
            return
        self.ctx.settings.accent = name
        self.window.rebuild()
        self.window.toasts.show(f"Accent colour set to {name}", "info")

    # ------------------------------------------------------------------ IDEs
    def _ide_section(self) -> None:
        box, body = controls.section(self.body, "IDEs",
                                     "Detected automatically for the current Windows user. Set a custom path if an "
                                     "IDE is installed somewhere else.", "code")
        box.pack(fill="x", pady=(0, theme.LG))
        self.detect_btn = controls.button(box.header, "Detect again", lambda: self.detect(refresh=True), "secondary",
                                          icon="refresh")
        self.detect_btn.pack(side="right")
        self.detect_spinner = Spinner(box.header, "Detecting…")
        table = controls.transparent(body)
        table.pack(fill="x")
        table.grid_columnconfigure(1, weight=1)
        for index, d in enumerate(DEFINITIONS):
            self._ide_row(table, index, d)

    def _ide_row(self, table, index: int, d: IDEDefinition) -> None:
        names = controls.transparent(table)
        names.grid(row=index, column=0, sticky="w", pady=6, padx=(0, theme.LG))
        controls.label(names, d.name, "body", "bold", width=160).pack(anchor="w")
        status = controls.label(names, "Checking…", "caption", color="muted")
        status.pack(anchor="w")
        entry = TextField(table, "Checking…")
        entry.set_value(self.ctx.settings.ide_paths().get(d.key, ""))
        entry.grid(row=index, column=1, sticky="ew", pady=6)
        entry.bind("<Return>", lambda _e, k=d.key: self._save_typed(k))
        entry.bind("<FocusOut>", lambda _e, k=d.key: self._save_typed(k))
        actions = controls.transparent(table)
        actions.grid(row=index, column=2, sticky="e", pady=6, padx=(theme.SM, 0))
        controls.button(actions, "Browse…", lambda k=d.key: self._browse(k), "secondary", height=32).pack(side="left")
        test = controls.button(actions, "Test", lambda k=d.key: self._test(k), "ghost", icon="run", height=32)
        test.pack(side="left", padx=(theme.XS, 0))
        clear = IconButton(actions, "close", lambda k=d.key: self._clear(k), "Remove custom path")
        clear.pack(side="left", padx=(theme.XS, 0))
        self.ide_rows[d.key] = {"status": status, "entry": entry, "test": test, "clear": clear,
                                "saved": entry.value}

    def detect(self, refresh: bool) -> None:
        self.detect_btn.configure(state="disabled")
        self.detect_spinner.pack(side="right", padx=theme.MD)
        self.detect_spinner.start()
        self.window.ensure_ides(self._render_ides, refresh=refresh)

    def _render_ides(self, ides: dict[str, IDE]) -> None:
        if not self.winfo_exists():
            return
        self.ides = ides
        self.detect_spinner.stop()
        self.detect_spinner.pack_forget()
        self.detect_btn.configure(state="normal")
        custom = self.ctx.settings.ide_paths()
        for key, row in self.ide_rows.items():
            ide = ides.get(key)
            row["entry"].set_value(custom.get(key, ""))
            row["saved"] = custom.get(key, "")
            if ide:
                row["status"].configure(text=f"Found · {ide.source_label}", text_color=theme.c("success"))
                row["entry"].configure(placeholder_text=ide.path)
            elif custom.get(key):
                row["status"].configure(text="Custom path not found", text_color=theme.c("danger"))
            else:
                row["status"].configure(text="Not found", text_color=theme.c("muted"))
                row["entry"].configure(placeholder_text="Not detected. Browse to the .exe to add it.")
            row["test"].configure(state="normal" if ide else "disabled")
        self._refresh_default_menu()

    def _save_path(self, key: str, path: str) -> None:
        self.ctx.settings.set_ide_path(key, path)
        self.ide_rows[key]["saved"] = normalize_path(path)
        self.window.toasts.show(f"Saved path for {ide_name(key)}" if path else f"Removed custom path for {ide_name(key)}",
                                "success")
        self.detect(refresh=True)

    def _save_typed(self, key: str) -> None:
        row = self.ide_rows[key]
        path = normalize_path(row["entry"].value)
        if path == row["saved"]:
            return
        if path and (not os.path.isfile(path) or not path.lower().endswith(".exe")):
            row["status"].configure(text="Choose an existing .exe file", text_color=theme.c("danger"))
            return
        self._save_path(key, path)

    def _browse(self, key: str) -> None:
        d = next(x for x in DEFINITIONS if x.key == key)
        path = filedialog.askopenfilename(parent=self.window, title=f"Locate {d.name}",
                                          filetypes=[(f"{d.name} ({d.exe})", d.exe), ("Programs", "*.exe")])
        if path:
            self.ide_rows[key]["entry"].set_value(os.path.normpath(path))
            self._save_path(key, path)

    def _clear(self, key: str) -> None:
        if self.ide_rows[key]["saved"] or self.ide_rows[key]["entry"].value:
            self.ide_rows[key]["entry"].set_value("")
            self._save_path(key, "")

    def _test(self, key: str) -> None:
        ide = self.ides.get(key)
        if ide is None:
            return
        try:
            self.ctx.launcher.test_ide(ide)
            self.window.toasts.show(f"Launching {ide.name}…", "info")
        except LaunchError as exc:
            info(self.window, "Could not start the IDE", exc.user_message, "error")

    # ------------------------------------------------------------------ defaults
    def _defaults(self) -> None:
        box, body = controls.section(self.body, "Defaults", "Used when a project has no preferred IDE and for new "
                                                          "projects.", "settings")
        box.pack(fill="x", pady=(0, theme.LG))
        row = controls.transparent(body)
        row.pack(fill="x", pady=(0, theme.MD))
        controls.label(row, "Default IDE", "body", "bold", width=160).pack(side="left")
        self.default_ide_menu = controls.option_menu(row, [ASK_LABEL], self._set_default_ide, width=240)
        self.default_ide_menu.pack(side="left")
        controls.label(row, "  If none is set, DevDock asks which IDE to use.", "caption", color="muted").pack(side="left")
        row = controls.transparent(body)
        row.pack(fill="x")
        controls.label(row, "Default status", "body", "bold", width=160).pack(side="left")
        self.status_menu = controls.option_menu(row, STATUSES, self._set_default_status, width=240)
        self.status_menu.set(self.ctx.settings.default_status)
        self.status_menu.pack(side="left")
        self._default_labels: dict[str, str | None] = {ASK_LABEL: None}

    def _refresh_default_menu(self) -> None:
        current = self.ctx.settings.default_ide
        labels: dict[str, str | None] = {ASK_LABEL: None}
        for d in DEFINITIONS:
            if d.key in self.ides:
                labels[d.name] = d.key
        if current and current not in self.ides:
            labels[f"{ide_name(current)} (not found)"] = current
        self._default_labels = labels
        self.default_ide_menu.configure(values=list(labels))
        self.default_ide_menu.set(next((label for label, key in labels.items() if key == current), ASK_LABEL))

    def _set_default_ide(self, label: str) -> None:
        self.ctx.settings.default_ide = self._default_labels.get(label)
        self.window.notify_settings_changed()
        self.window.toasts.show(f"Default IDE: {label}", "success")

    def _set_default_status(self, status: str) -> None:
        self.ctx.settings.default_status = status
        self.window.toasts.show(f"New projects start as {status}", "success")

    # ------------------------------------------------------------------ data
    def _data(self) -> None:
        box, body = controls.section(self.body, "Data", "Your projects are stored locally in the data folder.",
                                     "database")
        box.pack(fill="x")
        path_row = controls.transparent(body)
        path_row.pack(fill="x", pady=(0, theme.MD))
        controls.label(path_row, "Data folder", "body", "bold", width=160).pack(side="left")
        controls.label(path_row, str(config.APP_DIR), "body", color="muted").pack(side="left")
        self.backup_label = controls.label(body, "", "caption", color="muted")
        self.backup_label.pack(anchor="w", pady=(0, theme.MD))
        buttons = controls.transparent(body)
        buttons.pack(fill="x")
        for text, command, icon, variant in (
                ("Export to JSON", self.export_json, "export", "secondary"),
                ("Import from JSON", self.import_json, "import", "secondary"),
                ("Open data folder", self.open_data_folder, "folder", "secondary"),
                ("Create backup now", self.backup_now, "database", "secondary"),
                ("Restore backup…", self.restore_backup, "refresh", "danger_ghost")):
            controls.button(buttons, text, command, variant, icon=icon).pack(side="left", padx=(0, theme.SM))

    def _update_backup_label(self) -> None:
        latest = self.ctx.db.latest_backup()
        count = len(self.ctx.db.list_backups())
        self.backup_label.configure(
            text=f"Last backup: {latest.created:%Y-%m-%d %H:%M} ({latest.reason}) · {count} backups kept"
            if latest else "No backups yet. DevDock makes one automatically every day.")

    def export_json(self) -> None:
        path = filedialog.asksaveasfilename(parent=self.window, title="Export projects",
                                            defaultextension=".json",
                                            initialfile=f"devdock-projects-{datetime.now():%Y%m%d}.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            count = self.ctx.projects.export_json(path)
        except DevDockError as exc:
            info(self.window, exc.title, exc.user_message, "error")
            return
        self.window.toasts.show(f"Exported {count} projects")

    def import_json(self) -> None:
        path = filedialog.askopenfilename(parent=self.window, title="Import projects",
                                          filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            items = self.ctx.projects.read_export(path)
        except DevDockError as exc:
            info(self.window, exc.title, exc.user_message, "error")
            return
        policy = MessageDialog(
            self.window, "Import projects",
            f"The file contains {len(items)} project(s). What should happen when a project with the same name "
            "already exists?", "question",
            (("Skip duplicates", "skip", "primary"), ("Import as copies", "rename", "secondary"),
             ("Cancel", None, "ghost"))).show()
        if not policy:
            return
        result = self.ctx.projects.import_projects(items, policy)
        self.window.toasts.show(f"Imported {result.added} project(s), skipped {result.skipped}",
                                "success" if result.added else "info")
        if result.errors:
            info(self.window, "Some entries were not imported", f"{len(result.errors)} entr"
                 f"{'y was' if len(result.errors) == 1 else 'ies were'} invalid.", "warning",
                 detail="\n".join(result.errors))
        self.window.notify_data_changed()
        self.window.refresh_missing()

    def open_data_folder(self) -> None:
        try:
            self.ctx.launcher.open_folder(str(config.APP_DIR))
        except LaunchError as exc:
            info(self.window, "Could not open the folder", exc.user_message, "error")

    def backup_now(self) -> None:
        try:
            path = self.ctx.db.backup("manual")
        except Exception as exc:
            log.exception("Manual backup failed")
            info(self.window, "Backup failed", "The backup could not be created.", "error", detail=str(exc))
            return
        self._update_backup_label()
        self.window.toasts.show(f"Backup saved: {path.name}")

    def restore_backup(self) -> None:
        path = BackupPickerDialog(self.window, self.ctx.db.list_backups()).show()
        if not path:
            return
        if not confirm(self.window, "Restore this backup?",
                       "All current projects and settings are replaced by the backup. A safety backup of the "
                       "current data is made first.", "Restore"):
            return
        try:
            self.ctx.db.restore(path)
        except DevDockError as exc:
            info(self.window, exc.title, exc.user_message, "error", detail=exc.detail)
            return
        self.ctx.git.invalidate()
        self.ctx.ide_detector.invalidate()
        self.window.toasts.show("Backup restored")
        theme.apply_mode(self.ctx.settings.theme)
        if self.ctx.settings.accent != theme.accent_name():
            self.window.rebuild()
        else:
            self.window.notify_settings_changed()
            self.refresh()
        self.window.refresh_missing()
