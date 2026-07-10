import customtkinter as ctk
import config


class StatCard(ctk.CTkFrame):

    def __init__(self, parent, title, value):

        super().__init__(
            parent,
            width=220,
            height=130,
            fg_color=config.CARD,
            corner_radius=15
        )

        self.pack_propagate(False)

        title_label = ctk.CTkLabel(
            self,
            text=title,
            font=("Segoe UI", 16),
            text_color=config.TEXT_SECONDARY
        )

        title_label.pack(pady=(20, 5))

        value_label = ctk.CTkLabel(
            self,
            text=value,
            font=("Segoe UI", 34, "bold"),
            text_color=config.TEXT
        )

        value_label.pack()