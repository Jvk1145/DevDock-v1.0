import customtkinter as ctk
import config


class Sidebar(ctk.CTkFrame):

    def __init__(
        self,
        parent,
        show_dashboard,
        show_add_project,
        show_settings
    ):

        super().__init__(
            parent,
            width=250,
            corner_radius=0,
            fg_color=config.SIDEBAR
        )

        self.pack_propagate(False)

        # -------------------------
        # App Title
        # -------------------------

        ctk.CTkLabel(
            self,
            text="🚀 DevDock",
            font=("Segoe UI", 26, "bold"),
            text_color=config.TEXT
        ).pack(pady=(30, 40))

        # -------------------------
        # Dashboard
        # -------------------------

        ctk.CTkButton(
            self,
            text="🏠 Dashboard",
            width=200,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            hover_color=config.PRIMARY,
            anchor="w",
            command=show_dashboard
        ).pack(pady=6, padx=20)

        # -------------------------
        # Add Project
        # -------------------------

        ctk.CTkButton(
            self,
            text="➕ Add Project",
            width=200,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            hover_color=config.PRIMARY,
            anchor="w",
            command=show_add_project
        ).pack(pady=6, padx=20)

        # -------------------------
        # Settings
        # -------------------------

        ctk.CTkButton(
            self,
            text="⚙ Settings",
            width=200,
            height=42,
            corner_radius=10,
            fg_color="transparent",
            hover_color=config.PRIMARY,
            anchor="w",
            command=show_settings
        ).pack(pady=6, padx=20)

        self.show_dashboard = show_dashboard
        self.show_add_project = show_add_project
        self.show_settings = show_settings