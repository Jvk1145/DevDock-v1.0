import customtkinter as ctk
import config

from ui.components.sidebar import Sidebar
from ui.components.topbar import TopBar
from ui.pages.dashboard import Dashboard
from ui.pages.add_project import AddProject
from database.database import db

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
        self.sidebar = Sidebar(
            self,
            self.show_dashboard,
            self.show_add_project
        )
        self.sidebar.pack(side="left", fill="y")

        # Main Frame
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

        # Content Area
        self.content = ctk.CTkFrame(
            self.main_frame,
            fg_color=config.BACKGROUND
        )
        self.content.pack(
            fill="both",
            expand=True
        )

        # Open Dashboard on startup
        self.show_dashboard()

    # -----------------------------
    # Navigation Methods
    # -----------------------------

    def clear_content(self):
        """Remove everything from the content area"""
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_content()

        dashboard = Dashboard(self.content)
        dashboard.pack(fill="both", expand=True)

    def show_add_project(self):
        self.clear_content()

        add_project = AddProject(
            self.content,
            self.show_dashboard
        )



if __name__ == "__main__":
    app = DevDock()
    app.mainloop()
