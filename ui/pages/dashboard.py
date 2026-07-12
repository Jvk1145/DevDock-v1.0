import customtkinter as ctk

from database.database import db
from ui.components.stat_card import StatCard
from ui.components.project_card import ProjectCard


class Dashboard(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        # ===========================
        # Get Projects from Database
        # ===========================

        projects = db.get_projects()

        if len(projects) == 0:
            empty_label = ctk.CTkLabel(
                self,
                text="📂\n\nNo Projects Yet\n\nClick 'Add Project' to create your first project.",
                font=("Segoe UI", 22),
                justify="center"
            )

            empty_label.pack(expand=True)

            return
        active_projects = 0
        completed_projects = 0
        total_projects = len(projects)



        for project in projects:
            if project[4] == "Active":
                active_projects += 1
            elif project[4] == "Completed":
                completed_projects += 1

        # ===========================
        # Statistics
        # ===========================

        stats_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        stats_frame.pack(
            pady=25,
            padx=25,
            anchor="nw"
        )

        StatCard(
            stats_frame,
            "Projects",
            str(total_projects)
        ).pack(side="left", padx=10)

        StatCard(
            stats_frame,
            "Active",
            str(active_projects)
        ).pack(side="left", padx=10)

        StatCard(
            stats_frame,
            "Completed",
            str(completed_projects)
        ).pack(side="left", padx=10)

        # ===========================
        # Projects
        # ===========================

        projects_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        projects_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        for project in projects:

            ProjectCard(
                projects_frame,
                project[1],      # Project Name
                project[3],      # Technology
                project[4]       # Status
            )