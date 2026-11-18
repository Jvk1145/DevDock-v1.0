"""Project card used in grid and list views. Cards are reused and updated in place."""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import customtkinter as ctk

from core import timeutil
from core.models import GitInfo, Project
from ui import icons, theme
from ui.widgets import controls
from ui.widgets.badge import Badge
from ui.widgets.icon_button import IconButton
from ui.widgets.spinner import Spinner

if TYPE_CHECKING:
    from ui.main_window import MainWindow

MAX_TAGS_SHOWN = 3


def fit_text(text: str, max_chars: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    cut = text[: max(1, max_chars - 1)]
    if " " in cut[max_chars // 2:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;:-") + "…"


def git_summary(info: GitInfo) -> str:
    parts = [info.branch]
    parts.append("clean" if info.changes == 0 else f"{info.changes} change{'s' if info.changes != 1 else ''}")
    if info.last_commit_at:
        parts.append(timeutil.humanize(info.last_commit_at))
    return "  ·  ".join(parts)


class ProjectCard(ctk.CTkFrame):
    def __init__(self, master, window: "MainWindow", project: Project, layout: str = "grid",
                 missing: bool = False, on_select: Callable[[Project], None] | None = None):
        super().__init__(master, fg_color=theme.c("card"), corner_radius=theme.RADIUS_CARD, border_width=2,
                         border_color=theme.c("border"))
        self.window = window
        self.actions = window.actions
        self.layout = layout
        self.on_select = on_select
        self.project = project
        self.missing = missing
        self.selected = False
        self._hovering = False
        self._width = 0
        self._build()
        self.set_project(project, missing)
        self._bind_tree(self)
        self.bind("<Configure>", self._on_resize, add="+")

    # ------------------------------------------------------------------ construction
    def _build(self) -> None:
        pad = theme.LG
        grid = self.layout == "grid"
        self.grid_columnconfigure(0, weight=1)

        self.info = controls.transparent(self)
        header = controls.transparent(self.info)
        header.pack(fill="x")
        self.name_label = controls.label(header, "", "subtitle", "bold")
        self.star = IconButton(header, "star", self._toggle_favorite, "Pin to dashboard", size=28, icon_size=16)
        if grid:
            self.name_label.pack(side="left", fill="x", expand=True)
            self.star.pack(side="right")
        else:
            self.name_label.pack(side="left")
            self.star.pack(side="left", padx=(theme.XS, 0))
        self.desc_label = controls.label(self.info, "", "body", color="muted", height=40 if grid else 20,
                                         anchor="nw")
        self.desc_label.pack(fill="x", pady=(2, 0))

        self.chips = controls.transparent(self)
        self.meta = controls.transparent(self)
        self.git_label = controls.label(self.meta, "", "caption", color="muted", compound="left",
                                        image=icons.get("git", 13, "muted"))
        self.spinner = Spinner(self.meta, "Reading git…")
        self.opened_label = controls.label(self.meta, "", "caption", color="muted", compound="left",
                                           image=icons.get("clock", 13, "muted"))

        self.actions_row = controls.transparent(self)
        self.open_btn = controls.button(self.actions_row, "Open", self._open, "primary", icon="code", height=34)
        self.icon_buttons = {
            "folder": IconButton(self.actions_row, "folder", lambda: self.actions.open_folder(self.project),
                                 "Open folder"),
            "terminal": IconButton(self.actions_row, "terminal", lambda: self.actions.open_terminal(self.project),
                                   "Open terminal here"),
            "github": IconButton(self.actions_row, "git", lambda: self.actions.open_github(self.project),
                                 "Open GitHub repository"),
            "run": IconButton(self.actions_row, "run", lambda: self.actions.run(self.project), "Run start command"),
            "edit": IconButton(self.actions_row, "edit", lambda: self.actions.edit(self.project), "Edit project"),
            "delete": IconButton(self.actions_row, "delete", lambda: self.actions.delete(self.project),
                                 "Delete project", danger=True),
        }

        if grid:
            self.info.grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, theme.SM))
            self.chips.grid(row=1, column=0, sticky="ew", padx=pad, pady=(0, theme.SM))
            self.meta.grid(row=2, column=0, sticky="ew", padx=pad, pady=(0, theme.MD))
            self.actions_row.grid(row=3, column=0, sticky="ew", padx=pad, pady=(0, pad))
        else:
            self.grid_columnconfigure(1, weight=0)
            self.info.grid(row=0, column=0, sticky="ew", padx=(pad, theme.MD), pady=(theme.MD, 2))
            self.meta.grid(row=1, column=0, sticky="ew", padx=(pad, theme.MD), pady=(0, theme.MD))
            self.chips.grid(row=0, column=1, rowspan=2, sticky="e", padx=theme.MD)
            self.actions_row.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, pad))

    def _bind_tree(self, widget) -> None:
        """Hover, click-to-select and double-click-to-launch on the card and its non-button parts."""
        for sequence, handler in (("<Enter>", self._enter), ("<Leave>", self._leave),
                                  ("<Button-1>", self._click), ("<Double-Button-1>", self._double)):
            if isinstance(widget, ctk.CTkButton) and sequence not in ("<Enter>", "<Leave>"):
                continue
            widget.bind(sequence, handler, add="+")
        if isinstance(widget, ctk.CTkButton):
            return
        for child in widget.winfo_children():
            self._bind_tree(child)

    # ------------------------------------------------------------------ data
    def set_project(self, project: Project, missing: bool) -> None:
        self.project = project
        self.missing = missing
        self.name_label.configure(text=project.name)
        self.star.set_icon("star_filled" if project.favorite else "star", "warning" if project.favorite else "muted")
        self.star.set_tooltip("Unpin from dashboard" if project.favorite else "Pin to dashboard")

        for child in self.chips.winfo_children():
            child.destroy()
        side = "left" if self.layout == "grid" else "right"
        badges: list[tuple[str, str]] = []
        badges.append(("Missing", "danger") if missing else (project.status, theme.status_token(project.status)))
        if project.technology:
            badges.append((project.technology, "accent"))
        for tag in project.tags[:MAX_TAGS_SHOWN]:
            badges.append((f"#{tag}", "muted"))
        if len(project.tags) > MAX_TAGS_SHOWN:
            badges.append((f"+{len(project.tags) - MAX_TAGS_SHOWN}", "muted"))
        if self.layout != "grid":
            badges.reverse()
        for text, token in badges:
            badge = Badge(self.chips, text, token)
            badge.pack(side=side, padx=(0, 6) if side == "left" else (6, 0))
            self._bind_tree(badge)

        opened = timeutil.humanize(project.last_opened)
        self.opened_label.configure(text=f" Opened {opened}" if opened else " Never opened")

        for btn in self.icon_buttons.values():
            btn.pack_forget()
        self.open_btn.pack_forget()
        if missing:
            self.open_btn.configure(text="Relocate", command=lambda: self.actions.relocate(self.project))
            controls.restyle_button(self.open_btn, "danger", "folder")
        else:
            self.open_btn.configure(text=self.window.ide_label_for(project), command=self._open)
            controls.restyle_button(self.open_btn, "primary", "code")
        visible = ["edit", "delete"]
        if not missing:
            visible = ["folder", "terminal"] + (["github"] if project.github_url else []) + \
                      (["run"] if project.start_command else []) + visible
        # Icon buttons are packed first (right to left) so they always stay visible; the Open
        # button takes whatever width is left.
        for key in reversed(visible):
            self.icon_buttons[key].pack(side="right", padx=0)
        if self.layout == "grid":
            self.open_btn.pack(side="left", fill="x", expand=True, padx=(0, theme.SM))
        else:
            self.open_btn.pack(side="left", padx=(0, theme.SM))
        self._update_description()
        self.load_git()

    def _update_description(self) -> None:
        scale = ctk.ScalingTracker.get_widget_scaling(self) or 1.0
        width = (self._width or (330 if self.layout == "grid" else 1000) * scale) / scale
        if self.layout == "grid":
            usable = width - 2 * theme.LG - 8
        else:   # what is left between the left edge and the badges + buttons
            taken = (self.chips.winfo_reqwidth() + self.actions_row.winfo_reqwidth()) / scale
            usable = width - taken - 2 * theme.LG - 2 * theme.MD - 16
        usable = max(120, usable)
        per_line = int(usable / 6.8)
        lines = 2 if self.layout == "grid" else 1
        text = self.project.description or ("No description" if self.layout == "grid" else "")
        self.desc_label.configure(text=fit_text(text, per_line * lines), wraplength=int(usable))

    def _on_resize(self, event) -> None:
        # CTkFrame.bind() binds its internal canvas, so the event comes from that canvas.
        if event.widget in (self, self._canvas) and abs(event.width - self._width) > 8:
            self._width = event.width
            self._update_description()

    # ------------------------------------------------------------------ git
    def load_git(self) -> None:
        git = self.window.ctx.git
        self.git_label.pack_forget()
        self.spinner.pack_forget()
        self.opened_label.pack_forget()
        if self.missing or not git.available:
            self._show_meta(None)
            return
        fresh, info = git.cached(self.project.folder_path)
        if fresh:
            self._show_meta(info)
            return
        self.spinner.pack(side="left", padx=(0, theme.LG))
        self.spinner.start()
        self.opened_label.pack(side="left")
        folder = self.project.folder_path
        self.window.runner.watch(git.submit(folder), on_success=lambda i, f=folder: self._git_loaded(f, i),
                                 on_error=lambda _e: self._show_meta(None), owner=self)

    def _git_loaded(self, folder: str, info: GitInfo | None) -> None:
        if folder == self.project.folder_path:
            self._show_meta(info)

    def _show_meta(self, info: GitInfo | None) -> None:
        self.spinner.stop()
        self.spinner.pack_forget()
        self.git_label.pack_forget()
        self.opened_label.pack_forget()
        if info is not None:
            self.git_label.configure(text=f" {git_summary(info)}")
            self.git_label.pack(side="left", padx=(0, theme.LG))
        self.opened_label.pack(side="left")

    # ------------------------------------------------------------------ interaction
    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.configure(border_color=theme.c("accent") if selected else theme.c("border"))

    def _open(self) -> None:
        self.actions.launch(self.project)

    def _toggle_favorite(self) -> None:
        self.actions.toggle_favorite(self.project)

    def _click(self, _event=None) -> None:
        if self.on_select:
            self.on_select(self.project)

    def _double(self, _event=None) -> None:
        if self.missing:
            self.actions.relocate(self.project)
        else:
            self.actions.launch(self.project)

    def _enter(self, _event=None) -> None:
        if not self._hovering:
            self._hovering = True
            self.configure(fg_color=theme.c("card_hover"))

    def _leave(self, _event=None) -> None:
        self.after(20, self._check_leave)

    def _check_leave(self) -> None:
        try:
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)
        except Exception:
            widget = None
        while widget is not None:
            if widget is self:
                return
            widget = getattr(widget, "master", None)
        if self._hovering:
            self._hovering = False
            try:
                self.configure(fg_color=theme.c("card"))
            except Exception:
                pass
