"""Add / edit project form with inline validation."""
from __future__ import annotations

import os
from tkinter import filedialog

import customtkinter as ctk

from core import tech_detector
from core.errors import DevDockError, NotFoundError, ValidationError
from core.ide_detector import DEFINITIONS, ide_name
from core.models import ASK_EVERY_TIME, IDE, Project
from core.validators import STATUSES, normalize_path, parse_tags, validate_project
from ui import theme
from ui.pages.base import Page
from ui.widgets import controls
from ui.widgets.text_field import TextField

USE_DEFAULT = "Use default IDE"
ASK_LABEL = "Ask every time"


class ProjectFormPage(Page):
    key = "form"

    def __init__(self, master, window):
        super().__init__(master, window)
        self.project: Project | None = None
        self.touched: set[str] = set()
        self.submitted = False
        self._auto_tech = ""
        self._auto_name = ""
        self._ide_labels: dict[str, str | None] = {USE_DEFAULT: None, ASK_LABEL: ASK_EVERY_TIME}
        self._loading = False
        self._build()

    # ------------------------------------------------------------------ titles
    @property
    def editing(self) -> bool:
        return self.project is not None

    @property
    def title(self) -> str:  # type: ignore[override]
        return "Edit project" if self.editing else "Add project"

    @property
    def subtitle(self) -> str:  # type: ignore[override]
        return self.project.name if self.project else "Register a project folder"

    @property
    def nav_key(self) -> str:  # type: ignore[override]
        return "projects" if self.editing else "form"

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        scroll = controls.scroll_frame(self)
        scroll.pack(fill="both", expand=True)
        box = controls.card(scroll, width=760)
        box.pack(pady=theme.XL, padx=theme.XL)
        form = controls.transparent(box)
        form.pack(fill="both", expand=True, padx=theme.XXL, pady=theme.XL)
        form.grid_columnconfigure((0, 1), weight=1, uniform="half")
        self.heading = controls.label(form, "", "title", "bold")
        self.heading.grid(row=0, column=0, columnspan=2, sticky="w")
        controls.label(form, "Fields marked * are required. Ctrl+S saves, Esc cancels.", "caption",
                       color="muted").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, theme.LG))

        self.vars = {name: ctk.StringVar() for name in ("technology", "status", "ide")}
        self.fields: dict[str, TextField] = {}
        self.errors: dict[str, ctk.CTkLabel] = {}
        row = 2

        def field(name: str, label: str, widget, column: int = 0, span: int = 2, required: bool = False,
                  hint: str = "") -> None:
            nonlocal row
            cell = controls.transparent(form)
            cell.grid(row=row, column=column, columnspan=span, sticky="ew",
                      padx=(0, theme.MD) if span == 1 and column == 0 else 0)
            controls.field_label(cell, label, required).pack(anchor="w", pady=(0, theme.XS))
            widget(cell).pack(fill="x")
            err = controls.error_label(cell)
            err.pack(anchor="w", fill="x")
            if hint:
                err.configure(text=hint, text_color=theme.c("muted"))
                err.hint = hint  # type: ignore[attr-defined]
            self.errors[name] = err
            if span == 2 or column == 1:
                row += 1

        field("name", "Project name", lambda p: self._entry(p, "name", "My awesome app"), required=True)

        def description(parent):
            self.description = ctk.CTkTextbox(parent, height=84, font=theme.font("body"), wrap="word")
            self.description.bind("<KeyRelease>", lambda _e: self._changed("description"))
            return self.description
        field("description", "Description", description)

        def folder(parent):
            holder = controls.transparent(parent)
            entry = self._entry(holder, "folder_path", r"C:\Projects\my-app")
            entry.pack(side="left", fill="x", expand=True)
            controls.button(holder, "Browse…", self.browse, "secondary", icon="folder").pack(side="left",
                                                                                           padx=(theme.SM, 0))
            return holder
        field("folder_path", "Project folder", folder, required=True)

        def technology(parent):
            self.tech_combo = controls.combo(parent, list(tech_detector.TECHNOLOGIES), variable=self.vars["technology"],
                                             command=lambda _v: self._changed("technology"))
            self.vars["technology"].trace_add("write", lambda *_: self._changed("technology"))
            return self.tech_combo
        field("technology", "Technology", technology, 0, 1, hint="Detected from the folder; you can change it.")

        def status(parent):
            return controls.option_menu(parent, STATUSES, lambda _v: self._changed("status"),
                                        variable=self.vars["status"])
        field("status", "Status", status, 1, 1)

        def ide(parent):
            self.ide_menu = controls.option_menu(parent, [USE_DEFAULT, ASK_LABEL], lambda _v: self._changed("ide"),
                                                 variable=self.vars["ide"])
            return self.ide_menu
        field("ide", "Preferred IDE", ide, 0, 1)
        field("github_url", "GitHub URL", lambda p: self._entry(p, "github_url", "https://github.com/you/repo"), 1, 1)
        field("start_command", "Start command",
              lambda p: self._entry(p, "start_command", "streamlit run app.py"),
              hint="Runs in a new terminal inside the project folder.")
        field("tags", "Tags", lambda p: self._entry(p, "tags", "portfolio, client, ml"),
              hint="Separate tags with commas.")

        buttons = controls.transparent(form)
        buttons.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(theme.MD, 0))
        ctk.CTkFrame(form, width=700, height=0, fg_color="transparent").grid(row=row + 1, column=0, columnspan=2)
        self.save_btn = controls.button(buttons, "Save project", self.save, "primary", icon="check", width=150)
        self.save_btn.pack(side="right")
        controls.button(buttons, "Cancel", self.cancel, "secondary", width=100).pack(side="right", padx=(0, theme.SM))
        self.form_error = controls.label(buttons, "", "caption", color="danger")
        self.form_error.pack(side="left")

    def _entry(self, parent, name: str, placeholder: str) -> TextField:
        entry = TextField(parent, placeholder, lambda _text: self._changed(name))
        entry.bind("<FocusOut>", lambda _e: self._touch(name))
        self.fields[name] = entry
        if name == "name":
            self.name_entry = entry
        return entry

    def _get(self, name: str) -> str:
        return self.fields[name].value if name in self.fields else self.vars[name].get()

    def _set(self, name: str, value: str) -> None:
        if name in self.fields:
            self.fields[name].set_value(value)
        else:
            self.vars[name].set(value)

    # ------------------------------------------------------------------ loading
    def on_show(self, project_id: int | None = None, **_kwargs) -> None:
        self._loading = True
        self.touched.clear()
        self.submitted = False
        self._auto_tech = self._auto_name = ""
        self.form_error.configure(text="")
        self.project = None
        if project_id is not None:
            try:
                self.project = self.ctx.projects.get(project_id)
            except NotFoundError:
                self.window.toasts.show("That project no longer exists.", "error")
        p = self.project or Project(name="", folder_path="", status=self.ctx.settings.default_status)
        for name, value in (("name", p.name), ("folder_path", p.folder_path), ("technology", p.technology),
                            ("status", p.status), ("github_url", p.github_url), ("start_command", p.start_command),
                            ("tags", ", ".join(p.tags))):
            self._set(name, value)
        self.description.delete("1.0", "end")
        self.description.insert("1.0", p.description)
        self._set_ide_options({}, p.preferred_ide)
        self.window.ensure_ides(lambda ides: self._set_ide_options(ides, self._selected_ide_key()))
        self.heading.configure(text=self.title)
        self.save_btn.configure(text="Save changes" if self.editing else "Save project")
        self._loading = False
        self._validate()
        self.window.update_title()
        self.after(50, self.name_entry.focus_set)

    def _set_ide_options(self, ides: dict[str, IDE], selected_key: str | None) -> None:
        default_key = self.ctx.settings.default_ide
        default_label = f"{USE_DEFAULT} ({ide_name(default_key)})" if default_key else USE_DEFAULT
        labels: dict[str, str | None] = {default_label: None}
        for d in DEFINITIONS:
            if d.key in ides:
                labels[d.name] = d.key
        if selected_key and selected_key != ASK_EVERY_TIME and selected_key not in ides:
            labels[f"{ide_name(selected_key)} (not found)"] = selected_key
        labels[ASK_LABEL] = ASK_EVERY_TIME
        self._ide_labels = labels
        self.ide_menu.configure(values=list(labels))
        chosen = next((label for label, key in labels.items() if key == selected_key), default_label)
        self.vars["ide"].set(chosen)

    def _selected_ide_key(self) -> str | None:
        return self._ide_labels.get(self.vars["ide"].get())

    # ------------------------------------------------------------------ validation
    def _form_project(self) -> Project:
        base = self.project or Project(name="", folder_path="")
        return Project(
            id=base.id, name=self._get("name"), folder_path=self._get("folder_path"),
            description=self.description.get("1.0", "end").strip(), technology=self.vars["technology"].get(),
            status=self.vars["status"].get(), preferred_ide=self._selected_ide_key(),
            github_url=self._get("github_url"), live_demo=base.live_demo,
            start_command=self._get("start_command"), tags=parse_tags(self._get("tags")),
            favorite=base.favorite, created_at=base.created_at, last_opened=base.last_opened)

    def _touch(self, name: str) -> None:
        if name not in self.touched:
            self.touched.add(name)
            self._validate()

    def _changed(self, name: str) -> None:
        if self._loading:
            return
        self.touched.add(name)
        if name == "folder_path":
            self._folder_changed()
        self._validate()

    def _validate(self) -> dict[str, str]:
        project = self._form_project()
        exclude = project.id
        errors = validate_project(project, lambda n: self.ctx.projects.name_taken(n, exclude))
        for name, label in self.errors.items():
            message = errors.get(name) if (self.submitted or name in self.touched) else None
            if message:
                label.configure(text=message, text_color=theme.c("danger"))
            else:
                label.configure(text=getattr(label, "hint", ""), text_color=theme.c("muted"))
        self.save_btn.configure(state="disabled" if errors else "normal")
        return errors

    def _folder_changed(self) -> None:
        folder = normalize_path(self._get("folder_path"))
        if not folder or not os.path.isdir(folder):
            return
        if not self._get("name").strip() or self._get("name") == self._auto_name:
            self._auto_name = os.path.basename(folder.rstrip("\\/")) or folder
            self._loading = True
            self._set("name", self._auto_name)
            self._loading = False
        current = self.vars["technology"].get().strip()
        if current and current != self._auto_tech:
            return

        def detected(tech: str | None) -> None:
            if normalize_path(self._get("folder_path")) != folder or not tech:
                return
            if self.vars["technology"].get().strip() in ("", self._auto_tech):
                self._auto_tech = tech
                self._loading = True
                self.vars["technology"].set(tech)
                self._loading = False
                self.errors["technology"].configure(text=f"Detected: {tech}", text_color=theme.c("success"))
                self._validate()

        self.window.runner.submit(tech_detector.detect, folder, on_success=detected, owner=self)

    # ------------------------------------------------------------------ actions
    def browse(self) -> None:
        current = normalize_path(self._get("folder_path"))
        folder = filedialog.askdirectory(parent=self.window, title="Choose the project folder", mustexist=True,
                                         initialdir=current if os.path.isdir(current) else os.path.expanduser("~"))
        if folder:
            self.fields["folder_path"].set_value(os.path.normpath(folder), notify=True)
            self._touch("folder_path")

    def save(self) -> None:
        self.submitted = True
        if self._validate():
            self.form_error.configure(text="Please fix the highlighted fields.")
            return
        project = self._form_project()
        try:
            if self.editing:
                saved = self.ctx.projects.update(project)
                message = f"Saved changes to {saved.name}"
            else:
                saved = self.ctx.projects.create(project)
                message = f"Added {saved.name}"
        except ValidationError as exc:
            for name, text in exc.errors.items():
                if name in self.errors:
                    self.errors[name].configure(text=text, text_color=theme.c("danger"))
            self.form_error.configure(text=exc.user_message)
            return
        except DevDockError as exc:
            self.form_error.configure(text=exc.user_message)
            return
        self.ctx.missing_ids.discard(saved.id)
        self.ctx.git.invalidate(saved.folder_path)
        self.window.toasts.show(message)
        self.window.notify_data_changed()
        self.window.refresh_missing()
        self.window.navigate("projects")
        projects_page = self.window.pages.get("projects")
        if projects_page is not None:
            projects_page.select(saved)

    def cancel(self) -> None:
        self.window.back()

    def handle_key(self, action: str) -> bool:
        if action == "save":
            self.save()
            return True
        if action == "escape":
            self.cancel()
            return True
        return False
