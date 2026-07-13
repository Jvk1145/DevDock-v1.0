import customtkinter as ctk
import config

from ui.components.sidebar import Sidebar
from ui.components.topbar import TopBar

from ui.pages.dashboard import Dashboard
from ui.pages.add_project import AddProject
from ui.pages.settings import Settings

# Appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class DevDock(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Window
        self.title(config.APP_NAME)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(config.MIN_WIDTH, config.MIN_HEIGHT)
        self.configure(fg_color=config.BACKGROUND)

        # Sidebar
        self.sidebar = Sidebar(
            self,
            self.show_dashboard,
            self.show_add_project,
            self.show_settings
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

        # Topbar
        self.topbar = TopBar(self.main_frame)
        self.topbar.pack(fill="x")

        # Content
        self.content = ctk.CTkFrame(
            self.main_frame,
            fg_color=config.BACKGROUND
        )

        self.content.pack(
            fill="both",
            expand=True
        )

        self.show_dashboard()

    # ------------------------

    def clear_content(self):

        for widget in self.content.winfo_children():
            widget.destroy()

    # ------------------------

    def show_dashboard(self):

        self.clear_content()

        Dashboard(
            self.content
        ).pack(fill="both", expand=True)

    # ------------------------

    def show_add_project(self):

        self.clear_content()

        AddProject(
            self.content,
            self.show_dashboard
        ).pack(fill="both", expand=True)

    # ------------------------

    def show_settings(self):

        self.clear_content()

        Settings(
            self.content
        ).pack(fill="both", expand=True)


if __name__ == "__main__":
    app = DevDock()
    app.mainloop()