"""Projects page: responsive grid/list of project cards with search, filters and sorting."""
from __future__ import annotations

import customtkinter as ctk

from core.models import Project
from ui import theme
from ui.pages.base import Page
from ui.widgets import controls
from ui.widgets.badge import Chip
from ui.widgets.card_grid import CardGrid
from ui.widgets.empty_state import EmptyState
from ui.widgets.icon_button import IconButton
from ui.widgets.project_card import ProjectCard

ALL_TECH = "All technologies"
ALL_TAGS = "All tags"
SORT_LABELS = {"recent": "Recently opened", "name": "Name", "newest": "Newest"}
STATUS_FILTERS = ("All", "Active", "Completed", "On Hold", "Missing")


class ProjectsPage(Page):
    key = "projects"
    title = "Projects"
    subtitle = "All your projects in one place"

    def __init__(self, master, window):
        super().__init__(master, window)
        settings = self.ctx.settings
        self.search = ""
        self.status_filter = "All"
        self.technology: str | None = None
        self.tag: str | None = None
        self.sort = settings.sort
        self.view = settings.view_mode
        self.selected_id: int | None = None
        self.cards: dict[int, ProjectCard] = {}
        self.visible: list[Project] = []
        self._build()

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        toolbar = controls.transparent(self)
        toolbar.pack(fill="x", padx=theme.XL, pady=(theme.LG, theme.SM))
        chips = controls.transparent(toolbar)
        chips.pack(side="left")
        self.chips: dict[str, Chip] = {}
        for name in STATUS_FILTERS:
            chip = Chip(chips, name, lambda n=name: self.set_status_filter(n), selected=name == "All")
            chip.pack(side="left", padx=(0, 6))
            self.chips[name] = chip

        right = controls.transparent(toolbar)
        right.pack(side="right")
        self.list_btn = IconButton(right, "list", lambda: self.set_view("list"), "List view", size=34)
        self.list_btn.pack(side="right")
        self.grid_btn = IconButton(right, "grid", lambda: self.set_view("grid"), "Grid view", size=34)
        self.grid_btn.pack(side="right", padx=(0, 2))
        self.sort_menu = controls.option_menu(right, list(SORT_LABELS.values()), self._on_sort, width=150)
        self.sort_menu.set(SORT_LABELS[self.sort])
        self.sort_menu.pack(side="right", padx=(0, theme.MD))
        self.tag_menu = controls.option_menu(right, [ALL_TAGS], self._on_tag, width=130)
        self.tag_menu.pack(side="right", padx=(0, theme.SM))
        self.tech_menu = controls.option_menu(right, [ALL_TECH], self._on_tech, width=160)
        self.tech_menu.pack(side="right", padx=(0, theme.SM))

        info = controls.transparent(self)
        info.pack(fill="x", padx=theme.XL, pady=(0, theme.XS))
        self.count_label = controls.label(info, "", "caption", color="muted")
        self.count_label.pack(side="left")
        self.clear_btn = controls.button(info, "Clear filters", self.clear_filters, "ghost", height=24)

        self.scroll = controls.scroll_frame(self)
        self.scroll.pack(fill="both", expand=True, padx=theme.LG - theme.XS, pady=(0, theme.SM))
        self.grid_frame = CardGrid(self.scroll)
        self.grid_frame.pack(fill="x", expand=True)
        self.empty_holder = controls.transparent(self.scroll)
        self._update_view_buttons()

    # ------------------------------------------------------------------ filters
    def on_show(self, search: str | None = None, status: str | None = None, sort: str | None = None,
                **_kwargs) -> None:
        if search is not None:
            self.search = search
            self.window.topbar.search.set_text(search)
        else:
            self.search = self.window.topbar.search.get().strip()
        if status is not None:
            self.status_filter = status
        if sort is not None:
            self.sort = sort
            self.sort_menu.set(SORT_LABELS[sort])
        for name, chip in self.chips.items():
            chip.set_selected(name == self.status_filter)
        self.refresh()

    def on_search(self, text: str) -> None:
        self.search = text
        self.refresh(scroll_top=True)

    def set_status_filter(self, name: str) -> None:
        self.status_filter = name
        for key, chip in self.chips.items():
            chip.set_selected(key == name)
        self.refresh(scroll_top=True)

    def _on_tech(self, value: str) -> None:
        self.technology = None if value == ALL_TECH else value
        self.refresh(scroll_top=True)

    def _on_tag(self, value: str) -> None:
        self.tag = None if value == ALL_TAGS else value
        self.refresh(scroll_top=True)

    def _on_sort(self, label: str) -> None:
        self.sort = next(k for k, v in SORT_LABELS.items() if v == label)
        self.ctx.settings.sort = self.sort
        self.refresh(scroll_top=True)

    def set_view(self, view: str) -> None:
        if view == self.view:
            return
        self.view = view
        self.ctx.settings.view_mode = view
        for card in self.cards.values():
            card.destroy()
        self.cards.clear()
        self._update_view_buttons()
        self.refresh()

    def _update_view_buttons(self) -> None:
        self.grid_btn.set_active(self.view == "grid")
        self.list_btn.set_active(self.view == "list")

    def clear_filters(self) -> None:
        self.status_filter, self.technology, self.tag = "All", None, None
        self.tech_menu.set(ALL_TECH)
        self.tag_menu.set(ALL_TAGS)
        for key, chip in self.chips.items():
            chip.set_selected(key == "All")
        self.search = ""
        self.window.topbar.search.set_text("")
        self.refresh(scroll_top=True)

    def _filtered(self) -> bool:
        return bool(self.search or self.status_filter != "All" or self.technology or self.tag)

    # ------------------------------------------------------------------ data
    def refresh(self, scroll_top: bool = False) -> None:
        self.dirty = False
        service = self.ctx.projects
        status = self.status_filter if self.status_filter in ("Active", "Completed", "On Hold") else None
        projects = service.list_projects(search=self.search, status=status, technology=self.technology,
                                         tag=self.tag, sort=self.sort)
        missing = self.ctx.missing_ids
        if self.status_filter == "Missing":
            projects = [p for p in projects if p.id in missing]
        self.visible = projects
        self._refresh_menus(service.technologies(), service.all_tags())
        self.chips["Missing"].configure(text=f"Missing ({len(missing)})" if missing else "Missing")
        total = service.count()
        if self._filtered():
            self.count_label.configure(text=f"Showing {len(projects)} of {total} projects")
            self.clear_btn.pack(side="left", padx=theme.SM)
        else:
            self.count_label.configure(text=f"{total} project{'s' if total != 1 else ''}")
            self.clear_btn.pack_forget()
        self.subtitle = f"{total} project{'s' if total != 1 else ''} · {len(missing)} missing" if missing \
            else "All your projects in one place"
        self.window.update_title()
        self._render(projects, total)
        if scroll_top:
            self.scroll._parent_canvas.yview_moveto(0)

    def _refresh_menus(self, techs: list[str], tags: list[str]) -> None:
        self.tech_menu.configure(values=[ALL_TECH] + techs)
        if self.technology and self.technology not in techs:
            self.technology = None
        self.tech_menu.set(self.technology or ALL_TECH)
        self.tag_menu.configure(values=[ALL_TAGS] + tags)
        if self.tag and self.tag not in tags:
            self.tag = None
        self.tag_menu.set(self.tag or ALL_TAGS)

    def _render(self, projects: list[Project], total: int) -> None:
        for child in self.empty_holder.winfo_children():
            child.destroy()
        if not projects:
            self.grid_frame.set_cards([])
            self.empty_holder.pack(fill="both", expand=True)
            if total == 0:
                EmptyState(self.empty_holder, "empty", "No projects yet",
                           "Add a project folder to launch it in the right IDE with one click.",
                           "Add project", lambda: self.window.navigate("form"),
                           "Import folder", lambda: self.window.navigate("import")).pack(pady=theme.XL)
            else:
                EmptyState(self.empty_holder, "search", "No matching projects",
                           "Try a different search or clear the filters.").pack(pady=theme.XL)
                controls.button(self.empty_holder, "Clear filters", self.clear_filters, "secondary").pack()
            return
        self.empty_holder.pack_forget()
        missing = self.ctx.missing_ids
        ids = {p.id for p in projects}
        if self.selected_id not in ids:
            self.selected_id = None
        cards = []
        for project in projects:
            card = self.cards.get(project.id)
            is_missing = project.id in missing
            if card is None:
                card = ProjectCard(self.grid_frame, self.window, project, self.view, is_missing, self.select)
                self.cards[project.id] = card
            elif card.project != project or card.missing != is_missing:
                card.set_project(project, is_missing)
            card.set_selected(project.id == self.selected_id)
            cards.append(card)
        existing = self.ctx.projects.ids()
        for project_id in [i for i in self.cards if i not in existing]:
            self.cards.pop(project_id).destroy()
        self.grid_frame.set_cards(cards, self.view)

    # ------------------------------------------------------------------ selection & keys
    def select(self, project: Project | None) -> None:
        self.selected_id = project.id if project else None
        for project_id, card in self.cards.items():
            card.set_selected(project_id == self.selected_id)
        if project and project.id in self.cards:
            self._scroll_into_view(self.cards[project.id])

    def _selected(self) -> Project | None:
        return next((p for p in self.visible if p.id == self.selected_id), None)

    def _scroll_into_view(self, card: ProjectCard) -> None:
        self.update_idletasks()
        canvas = self.scroll._parent_canvas
        inner_height = max(1, self.scroll.winfo_height(), self.grid_frame.winfo_height())
        top = card.winfo_rooty() - self.grid_frame.winfo_rooty()
        bottom = top + card.winfo_height()
        view_top, view_bottom = canvas.canvasy(0), canvas.canvasy(canvas.winfo_height())
        if top < view_top:
            canvas.yview_moveto(max(0.0, top / inner_height))
        elif bottom > view_bottom:
            canvas.yview_moveto(max(0.0, (bottom - canvas.winfo_height()) / inner_height))

    def handle_key(self, action: str) -> bool:
        selected = self._selected()
        if action == "enter" and selected:
            card = self.cards.get(selected.id)
            if card and card.missing:
                self.window.actions.relocate(selected)
            else:
                self.window.actions.launch(selected)
            return True
        if action == "delete" and selected:
            self.window.actions.delete(selected)
            return True
        if action == "escape":
            if self.selected_id is not None:
                self.select(None)
                return True
            if self.search:
                self.window.topbar.search.set_text("", notify=False)
                self.on_search("")
                return True
            return False
        if action in ("up", "down", "left", "right") and self.visible:
            ids = [p.id for p in self.visible]
            step = {"left": -1, "right": 1, "up": -self.grid_frame.columns, "down": self.grid_frame.columns}[action]
            index = ids.index(self.selected_id) + step if self.selected_id in ids else 0
            index = max(0, min(len(ids) - 1, index))
            self.select(self.visible[index])
            return True
        return False
