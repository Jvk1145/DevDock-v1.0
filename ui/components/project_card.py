import customtkinter as ctk
import config


class ProjectCard(ctk.CTkFrame):

    def __init__(self, parent, name, tech, status):

        super().__init__(
            parent,
            fg_color=config.CARD,
            corner_radius=15,
            height=160
        )

        self.pack(fill="x", padx=20, pady=10)

        # Project Name
        title = ctk.CTkLabel(
            self,
            text=name,
            font=("Segoe UI", 22, "bold")
        )

        title.pack(anchor="w", padx=20, pady=(15, 5))

        # Technology
        tech_label = ctk.CTkLabel(
            self,
            text=tech,
            font=("Segoe UI", 14),
            text_color=config.TEXT_SECONDARY
        )

        tech_label.pack(anchor="w", padx=20)

        # Status
        status_label = ctk.CTkLabel(
            self,
            text=f"Status : {status}",
            font=("Segoe UI", 14)
        )

        status_label.pack(anchor="w", padx=20, pady=(5, 10))

        # Buttons Frame
        button_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        button_frame.pack(anchor="w", padx=20)

        launch_btn = ctk.CTkButton(
            button_frame,
            text="🚀 Launch",
            width=110
        )

        launch_btn.pack(side="left", padx=5)

        folder_btn = ctk.CTkButton(
            button_frame,
            text="📂 Folder",
            width=110
        )

        folder_btn.pack(side="left", padx=5)

        github_btn = ctk.CTkButton(
            button_frame,
            text="🌐 GitHub",
            width=110
        )

        github_btn.pack(side="left", padx=5)

