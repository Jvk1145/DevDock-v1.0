import customtkinter as ctk
import config


class ProjectCard(ctk.CTkFrame):

    def __init__(
        self,
        parent,
        project_id,
        name,
        tech,
        status,
        launch_command=None,
        delete_command=None,
        folder_command=None
    ):

        super().__init__(
            parent,
            fg_color=config.CARD,
            corner_radius=15,
            height=170
        )

        self.pack(
            fill="x",
            padx=20,
            pady=10
        )

        # -----------------------------
        # Project Name
        # -----------------------------

        ctk.CTkLabel(
            self,
            text=name,
            font=("Segoe UI", 22, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        # -----------------------------
        # Technology
        # -----------------------------

        ctk.CTkLabel(
            self,
            text=tech,
            text_color=config.TEXT_SECONDARY
        ).pack(
            anchor="w",
            padx=20
        )

        # -----------------------------
        # Status
        # -----------------------------

        ctk.CTkLabel(
            self,
            text=f"Status : {status}"
        ).pack(
            anchor="w",
            padx=20,
            pady=(5, 15)
        )

        # -----------------------------
        # Buttons
        # -----------------------------

        button_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        button_frame.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

        # Launch

        ctk.CTkButton(
            button_frame,
            text="🚀 Launch",
            width=110,
            command=launch_command
        ).pack(
            side="left",
            padx=5
        )

        # Open Folder

        ctk.CTkButton(
            button_frame,
            text="📂 Folder",
            width=110,
            command=folder_command
        ).pack(
            side="left",
            padx=5
        )

        # Delete

        ctk.CTkButton(
            button_frame,
            text="🗑 Delete",
            width=110,
            command=delete_command
        ).pack(
            side="left",
            padx=5
        )