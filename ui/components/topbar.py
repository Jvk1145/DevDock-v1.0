import customtkinter as ctk
import config


class TopBar(ctk.CTkFrame):

    def __init__(self, parent, search_command=None):
        super().__init__(
            parent,
            height=70,
            fg_color=config.CARD,
            corner_radius=0
        )

        self.search_command = search_command

        self.pack_propagate(False)

        # ===========================
        # Title
        # ===========================

        title = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=("Segoe UI", 24, "bold"),
            text_color=config.TEXT
        )

        title.pack(
            side="left",
            padx=25
        )




    # ===========================
    # Search Event
    # ===========================

    def on_search(self, event):

        if self.search_command:
            self.search_command(
                self.search.get()
            )