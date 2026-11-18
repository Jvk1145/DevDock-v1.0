"""Dashboard: greeting, statistics, pinned projects and recently opened projects."""
from __future__ import annotations

from datetime import datetime

import config
from ui import theme
from ui.pages.base import Page
from ui.widgets import controls
from ui.widgets.card_grid import CardGrid
from ui.widgets.empty_state import EmptyState
from ui.widgets.project_card import ProjectCard
from ui.widgets.stat_card import StatCard

TIPS = [
    "Press Ctrl+N to add a project, or use Import to add a whole folder of projects at once.",
    "Set a preferred IDE per project. DevDock remembers it and opens the right tool every time.",
    "Add a start command such as “streamlit run app.py” to run your project from its card.",
    "Star a project to pin it to the top of this dashboard.",
]


def greeting(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


class DashboardPage(Page):
    key = "dashboard"
    title = "Dashboard"

    def __init__(self, master, window):
        super().__init__(master, window)
        self.scroll = controls.scroll_frame(self)
        self.scroll.pack(fill="both", expand=True, padx=theme.LG - theme.XS)
        self.content = controls.transparent(self.scroll)
        self.content.pack(fill="both", expand=True, padx=theme.XS)

    @property
    def subtitle(self) -> str:  # type: ignore[override]
        now = datetime.now()
        return f"{now:%A}, {now.day} {now:%B %Y}"

    def refresh(self) -> None:
        self.dirty = False
        for child in self.content.winfo_children():
            child.destroy()
        service = self.ctx.projects
        projects = service.list_projects()
        missing = self.ctx.missing_ids

        head = controls.transparent(self.content)
        head.pack(fill="x", padx=theme.SM, pady=(theme.XL, theme.LG))
        controls.label(head, greeting(), "header", "bold").pack(anchor="w")
        controls.label(head, "Here is what is happening with your projects." if projects else
                       f"Welcome to {config.APP_NAME}. Let's add your first project.", "body",
                       color="muted").pack(anchor="w")

        if not projects:
            EmptyState(self.content, "empty", "No projects yet",
                       "Add a project folder and DevDock will open it in the right IDE with one click.",
                       "Add project", lambda: self.window.navigate("form"),
                       "Import a folder", lambda: self.window.navigate("import"), tips=TIPS).pack(pady=(0, theme.XL))
            return

        stats = service.stats(projects, missing)
        row = controls.transparent(self.content)
        row.pack(fill="x", padx=theme.XS, pady=(0, theme.LG))
        tiles = [
            ("Total projects", stats["total"], "projects", "accent", lambda: self._open_list("All")),
            ("Active", stats["Active"], "run", "success", lambda: self._open_list("Active")),
            ("Completed", stats["Completed"], "check", "info", lambda: self._open_list("Completed")),
            ("On hold", stats["On Hold"], "clock", "warning", lambda: self._open_list("On Hold")),
            ("Missing folders", stats["missing"], "warning", "danger", lambda: self._open_list("Missing")),
        ]
        for column, (title, value, icon, token, command) in enumerate(tiles):
            row.grid_columnconfigure(column, weight=1, uniform="stat")
            StatCard(row, title, value, icon, token, command).grid(row=0, column=column, sticky="ew",
                                                                   padx=theme.MD // 2)

        pinned = [p for p in projects if p.favorite]
        self._section("Pinned", f"{len(pinned)}" if pinned else "", None)
        if pinned:
            self._cards(pinned)
        else:
            controls.label(self.content, "Star a project to pin it here for quick access.", "body",
                           color="muted").pack(anchor="w", padx=theme.SM, pady=(0, theme.LG))

        recent = service.recent(config.RECENT_LIMIT)
        self._section("Recently opened", "", ("View all", lambda: self.window.navigate("projects", sort="recent")))
        if recent:
            self._cards(recent)
        else:
            controls.label(self.content, "Projects you open from DevDock will show up here.", "body",
                           color="muted").pack(anchor="w", padx=theme.SM, pady=(0, theme.LG))

    def _section(self, title: str, count: str, action) -> None:
        bar = controls.transparent(self.content)
        bar.pack(fill="x", padx=theme.SM, pady=(theme.MD, theme.SM))
        controls.label(bar, title, "subtitle", "bold").pack(side="left")
        if count:
            controls.label(bar, f"  {count}", "body", color="muted").pack(side="left")
        if action:
            controls.button(bar, action[0], action[1], "ghost", height=28).pack(side="right")

    def _cards(self, projects) -> None:
        grid = CardGrid(self.content)
        grid.pack(fill="x", pady=(0, theme.MD))
        missing = self.ctx.missing_ids
        cards = [ProjectCard(grid, self.window, p, "grid", p.id in missing) for p in projects]
        grid.set_cards(cards)

    def _open_list(self, status: str) -> None:
        self.window.navigate("projects", status=status)
