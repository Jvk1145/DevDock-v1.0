import customtkinter as ctk
import config


class Sidebar(ctk.CTkFrame):


    def __init__(self, parent, show_dashboard, show_add_project):
        super().__init__(
            parent,
            width=250,
            corner_radius=0,
            fg_color=config.SIDEBAR
        )

        self.pack_propagate(False)

        # App Title
        title = ctk.CTkLabel(
            self,
            text="🚀 DevDock",
            font=("Segoe UI", 26, "bold"),
            text_color=config.TEXT
        )
        title.pack(pady=(30, 40))

        # Navigation Buttons

        dashboard_btn = ctk.CTkButton(
            self,
            text="🏠 Dashboard",
            width=200,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            hover_color=config.PRIMARY,
            anchor="w",
            command=show_dashboard
        )

        dashboard_btn.pack(pady=6, padx=20)

        add_project_btn = ctk.CTkButton(
            self,
            text="➕ Add Project",
            width=200,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            hover_color=config.PRIMARY,
            anchor="w",
            command=show_add_project
        )

        add_project_btn.pack(pady=6, padx=20)

        settings_btn = ctk.CTkButton(
            self,
            text="⚙ Settings",
            width=200,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            hover_color=config.PRIMARY,
            anchor="w"
        )

        settings_btn.pack(pady=6, padx=20)

        self.show_dashboard = show_dashboard
        self.show_add_project = show_add_project