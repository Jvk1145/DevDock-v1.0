import customtkinter as ctk
import config


class TopBar(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(
            parent,
            height=70,
            fg_color=config.CARD,
            corner_radius=0
        )

        self.pack_propagate(False)

        # Title
        title = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=("Segoe UI", 24, "bold"),
            text_color=config.TEXT
        )
        title.pack(side="left", padx=25)

        # Search Box
        search = ctk.CTkEntry(
            self,
            width=250,
            placeholder_text="Search Projects..."
        )
        search.pack(side="right", padx=25)