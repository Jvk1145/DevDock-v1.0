"""Modal dialogs. Every dialog is transient to the main window, grabs input, is centred on
the main window, comes to the front, takes focus and closes with Esc."""
from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog
from typing import Any, Sequence

import customtkinter as ctk

import config
from core.database import BackupInfo
from core.models import IDE
from ui import icons, theme
from ui.widgets import controls

log = logging.getLogger(__name__)

_KIND_ICONS = {"error": ("error", "danger"), "warning": ("warning", "warning"), "info": ("about", "info"),
               "success": ("check", "success"), "question": ("about", "accent")}


class Modal(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width: int = 460):
        self.parent_window = parent.winfo_toplevel()
        super().__init__(self.parent_window, fg_color=theme.c("surface"))
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(self.parent_window)
        self.result: Any = None
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda _e: self.cancel())
        self.body = controls.transparent(self)
        self.body.pack(fill="both", expand=True, padx=theme.XL, pady=theme.XL)
        ctk.CTkFrame(self.body, width=width - 2 * theme.XL, height=0, fg_color="transparent").pack()

    # -------------------------------------------------------------- helpers for subclasses
    def header(self, title: str, message: str = "", kind: str | None = None) -> None:
        row = controls.transparent(self.body)
        row.pack(fill="x", anchor="w")
        if kind:
            icon, token = _KIND_ICONS.get(kind, _KIND_ICONS["info"])
            controls.icon_circle(row, icon, token, 44, 22, base="surface").pack(side="left", anchor="n",
                                                                               padx=(0, theme.LG))
        text = controls.transparent(row)
        text.pack(side="left", fill="x", expand=True)
        controls.label(text, title, "subtitle", "bold", wraplength=360).pack(anchor="w")
        if message:
            controls.label(text, message, "body", color="muted", wraplength=360).pack(anchor="w", pady=(theme.XS, 0))

    def button_row(self) -> ctk.CTkFrame:
        row = controls.transparent(self.body)
        row.pack(fill="x", pady=(theme.XL, 0))
        return row

    def show(self) -> Any:
        """Display modally and block until closed. Returns ``self.result``."""
        self._present()
        self.parent_window.wait_window(self)
        return self.result

    def _present(self) -> None:
        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        try:
            px, py = self.parent_window.winfo_rootx(), self.parent_window.winfo_rooty()
            pw, ph = self.parent_window.winfo_width(), self.parent_window.winfo_height()
            if self.parent_window.state() == "iconic" or pw < 50:
                raise tk.TclError
            x, y = px + (pw - width) // 2, py + max(0, (ph - height) // 3)
        except tk.TclError:
            x = (self.winfo_screenwidth() - width) // 2
            y = (self.winfo_screenheight() - height) // 3
        self.wm_geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: self._safe(lambda: self.attributes("-topmost", False)))
        self._grab()
        self.focus_force()
        if config.APP_ICON.is_file():
            self.after(250, lambda: self._safe(lambda: self.iconbitmap(str(config.APP_ICON))))

    def _grab(self, attempt: int = 0) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            if attempt < 10:
                self.after(30, lambda: self._grab(attempt + 1))

    def _safe(self, fn) -> None:
        try:
            if self.winfo_exists():
                fn()
        except tk.TclError:
            pass

    def close(self, result: Any = None) -> None:
        self.result = result
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        try:
            self.parent_window.focus_force()
        except tk.TclError:
            pass

    def cancel(self) -> None:
        self.close(None)


class MessageDialog(Modal):
    """Message with any number of action buttons. Returns the chosen action key (or None)."""

    def __init__(self, parent, title: str, message: str, kind: str = "info",
                 actions: Sequence[tuple[str, Any, str]] = (("OK", True, "primary"),), detail: str | None = None):
        super().__init__(parent, title)
        self.header(title, message, kind)
        if detail:
            box = ctk.CTkTextbox(self.body, height=90, font=("Consolas", 11), wrap="word")
            box.insert("1.0", detail)
            box.configure(state="disabled")
            box.pack(fill="x", pady=(theme.LG, 0))
        row = self.button_row()
        first = None
        for text, key, variant in reversed(list(actions)):
            btn = controls.button(row, text, lambda k=key: self.close(k), variant)
            btn.pack(side="right", padx=(theme.SM, 0))
            first = btn
        self.bind("<Return>", lambda _e: self.close(actions[0][1]))
        if first is not None:
            first.focus_set()


def confirm(parent, title: str, message: str, confirm_text: str = "Delete", danger: bool = True) -> bool:
    actions = ((confirm_text, True, "danger" if danger else "primary"), ("Cancel", False, "secondary"))
    dialog = MessageDialog(parent, title, message, "warning" if danger else "question", actions)
    dialog.unbind("<Return>")  # destructive actions need an explicit click
    return bool(dialog.show())


def info(parent, title: str, message: str, kind: str = "info", detail: str | None = None) -> None:
    MessageDialog(parent, title, message, kind, (("OK", True, "primary"),), detail).show()


class ErrorDialog(Modal):
    """'Something went wrong' with Copy details and Open log folder."""

    def __init__(self, parent, title: str, message: str, details: str):
        super().__init__(parent, title, width=520)
        self.details = details
        self.header(title, message, "error")
        self.text = ctk.CTkTextbox(self.body, height=150, font=("Consolas", 11), wrap="none")
        self.text.insert("1.0", details)
        self.text.configure(state="disabled")
        self.details_visible = False
        row = self.button_row()
        controls.button(row, "Close", self.cancel, "primary").pack(side="right", padx=(theme.SM, 0))
        controls.button(row, "Open log folder", self.open_logs, "secondary", icon="folder").pack(side="right",
                                                                                                padx=(theme.SM, 0))
        self.copy_btn = controls.button(row, "Copy details", self.copy, "secondary")
        self.copy_btn.pack(side="right", padx=(theme.SM, 0))
        self.toggle_btn = controls.button(row, "Show details", self.toggle, "ghost")
        self.toggle_btn.pack(side="left")
        self.row = row

    def toggle(self) -> None:
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.text.pack(fill="both", expand=True, pady=(theme.LG, 0), before=self.row)
        else:
            self.text.pack_forget()
        self.toggle_btn.configure(text="Hide details" if self.details_visible else "Show details")
        self.update_idletasks()
        self.wm_geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")

    def copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.details)
        self.copy_btn.configure(text="Copied")
        self.after(1500, lambda: self._safe(lambda: self.copy_btn.configure(text="Copy details")))

    def open_logs(self) -> None:
        try:
            os.startfile(str(config.LOG_DIR))  # noqa: S606 - opens a folder in Explorer
        except OSError:
            log.exception("Could not open the log folder")


class IDEChooserDialog(Modal):
    """Pick an IDE for a launch. Returns (ide_key, remember) or None."""

    def __init__(self, parent, ides: dict[str, IDE], project_name: str, default_key: str | None = None):
        super().__init__(parent, "Choose an IDE", width=440)
        self.header("Choose an IDE", f"Open “{project_name}” with:")
        self.remember = ctk.BooleanVar(value=False)
        listing = controls.transparent(self.body)
        listing.pack(fill="x", pady=(theme.LG, 0))
        ordered = sorted(ides.values(), key=lambda i: (i.key != default_key, i.name.lower()))
        for index, ide in enumerate(ordered):
            btn = ctk.CTkButton(listing, text=f"{ide.name}", anchor="w", height=44, compound="left",
                                image=icons.get("code", 18, "accent"), font=theme.font("body", "bold"),
                                fg_color=theme.c("card"), hover_color=theme.c("card_hover"), text_color=theme.c("text"),
                                border_width=1, border_color=theme.c("border"), corner_radius=theme.RADIUS_INPUT,
                                command=lambda k=ide.key: self.close((k, self.remember.get())))
            btn.pack(fill="x", pady=3)
            if index < 9:
                self.bind(str(index + 1), lambda _e, k=ide.key: self.close((k, self.remember.get())))
            if index == 0:
                btn.focus_set()
        ctk.CTkCheckBox(self.body, text="Remember for this project", variable=self.remember,
                        font=theme.font("body")).pack(anchor="w", pady=(theme.LG, 0))
        row = self.button_row()
        controls.button(row, "Cancel", self.cancel, "secondary").pack(side="right")
        controls.label(row, "Tip: press 1–9 to pick", "caption", color="muted").pack(side="left")


class BackupPickerDialog(Modal):
    """Choose a backup to restore. Returns a path or None."""

    def __init__(self, parent, backups: list[BackupInfo]):
        super().__init__(parent, "Restore backup", width=520)
        self.header("Restore a backup", "The current data is backed up first, then replaced by the backup you pick.",
                    "warning")
        self.choice = ctk.StringVar(value="")
        listing = controls.scroll_frame(self.body, height=220, fg_color=theme.c("card"), corner_radius=theme.RADIUS_INPUT)
        listing.pack(fill="x", pady=(theme.LG, 0))
        if not backups:
            controls.label(listing, "No backups yet. Use “Create backup now” first.", color="muted").pack(
                anchor="w", padx=theme.MD, pady=theme.MD)
        for backup in backups:
            ctk.CTkRadioButton(listing, text=backup.label, value=str(backup.path), variable=self.choice,
                               font=theme.font("body"), command=self._update).pack(anchor="w", padx=theme.MD, pady=5)
        row = self.button_row()
        self.restore_btn = controls.button(row, "Restore", lambda: self.close(self.choice.get()), "danger",
                                           state="disabled")
        self.restore_btn.pack(side="right", padx=(theme.SM, 0))
        controls.button(row, "Cancel", self.cancel, "secondary").pack(side="right")
        controls.button(row, "Browse for a file…", self.browse, "ghost", icon="folder").pack(side="left")

    def _update(self) -> None:
        self.restore_btn.configure(state="normal" if self.choice.get() else "disabled")

    def browse(self) -> None:
        path = filedialog.askopenfilename(parent=self, title="Choose a DevDock backup",
                                          initialdir=str(config.BACKUP_DIR),
                                          filetypes=[("DevDock database", "*.db"), ("All files", "*.*")])
        if path:
            self.close(os.path.normpath(path))
