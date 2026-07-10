import customtkinter as ctk
import config


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent):
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
        menu_items = [
            "🏠 Dashboard",
            "📂 Projects",
            "➕ Add Project",
            "⭐ Favorites",
            "📊 Statistics",
            "⚙ Settings"
        ]

        for item in menu_items:
            btn = ctk.CTkButton(
                self,
                text=item,
                width=200,
                height=42,
                corner_radius=10,
                fg_color="transparent",
                hover_color=config.PRIMARY,
                anchor="w"
            )
            btn.pack(pady=6, padx=20)