import customtkinter as ctk
import config

from ui.components.sidebar import Sidebar
from ui.components.topbar import TopBar
from ui.pages.dashboard import Dashboard

# Appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DevDock(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Title
        self.title(config.APP_NAME)

        # Window Size
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")

        # Minimum Size
        self.minsize(config.MIN_WIDTH, config.MIN_HEIGHT)

        # Background Color
        self.configure(fg_color=config.BACKGROUND)

        # Sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.pack(side="left", fill="y")

        # Main Content
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color=config.BACKGROUND
        )
        self.main_frame.pack(
            side="right",
            fill="both",
            expand=True
        )

        # Top Bar
        self.topbar = TopBar(self.main_frame)
        self.topbar.pack(fill="x")

        self.dashboard = Dashboard(self.main_frame)
        self.dashboard.pack(fill="both", expand=True)
