import customtkinter as ctk

from ui.components.stat_card import StatCard
from ui.components.project_card import ProjectCard


class Dashboard(ctk.CTkFrame):

    def __init__(self, parent):

        super().__init__(parent)

        stats_frame = ctk.CTkFrame(self, fg_color="transparent")

        stats_frame.pack(
            pady=25,
            padx=25,
            anchor="nw"
        )

        StatCard(stats_frame, "Projects", "12").pack(side="left", padx=10)

        StatCard(stats_frame, "Active", "8").pack(side="left", padx=10)

        StatCard(stats_frame, "Completed", "4").pack(side="left", padx=10)

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

        ProjectCard(
            projects_frame,
            "Retail Sales Dashboard",
            "Python • Power BI",
            "Active"
        )

        ProjectCard(
            projects_frame,
            "AI Business Analytics",
            "Python • Flask",
            "In Progress"
        )