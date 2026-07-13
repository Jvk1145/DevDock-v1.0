import os
import subprocess
import webbrowser
import customtkinter as ctk
import glob

from database.database import db
from ui.components.stat_card import StatCard
from ui.components.project_card import ProjectCard


class Dashboard(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.refresh_dashboard()

    def detect_ides(self):

        ides = {}

        import glob

        paths = {
            "VS Code": [
                r"C:\Users\*\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                r"C:\Program Files\Microsoft VS Code\Code.exe"
            ],

            "Cursor": [
                r"C:\Users\*\AppData\Local\Programs\Cursor\Cursor.exe"
            ],

            "PyCharm": [
                r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe",
                r"C:\Program Files (x86)\JetBrains\PyCharm*\bin\pycharm64.exe"
            ],

            "Android Studio": [
                r"C:\Program Files\Android\Android Studio\bin\studio64.exe"
            ],

            "IntelliJ IDEA": [
                r"C:\Program Files\JetBrains\IntelliJ IDEA*\bin\idea64.exe"
            ]
        }

        for ide, locations in paths.items():

            for location in locations:

                result = glob.glob(location)

                if result:
                    ides[ide] = result[0]
                    break

        return ides

    # ===========================
    # Refresh Dashboard
    # ===========================

    def refresh_dashboard(self):

        for widget in self.winfo_children():
            widget.destroy()

        self.projects = db.get_projects()

        if not self.projects:
            ctk.CTkLabel(
                self,
                text="📂\n\nNo Projects Yet\n\nClick 'Add Project' to create your first project.",
                font=("Segoe UI", 22),
                justify="center"
            ).pack(expand=True)
            return

        total = len(self.projects)
        active = sum(1 for p in self.projects if p[4] == "Active")
        completed = sum(1 for p in self.projects if p[4] == "Completed")

        # ===========================
        # Statistics
        # ===========================

        stats = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        stats.pack(
            pady=25,
            padx=25,
            anchor="nw"
        )

        StatCard(stats, "Projects", str(total)).pack(side="left", padx=10)
        StatCard(stats, "Active", str(active)).pack(side="left", padx=10)
        StatCard(stats, "Completed", str(completed)).pack(side="left", padx=10)

        # ===========================
        # Project Cards
        # ===========================

        projects_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        projects_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        for project in self.projects:

            ProjectCard(
                projects_frame,
                project[0],      # ID
                project[1],      # Name
                project[3],      # Technology
                project[4],      # Status

                launch_command=lambda pid=project[0]: self.launch_project(pid),

                delete_command=lambda pid=project[0]: self.delete_project(pid),

                folder_command=lambda pid=project[0]: self.open_project_folder(pid)
            )

    # ===========================
    # Delete Project
    # ===========================

    def delete_project(self, project_id):

        db.delete_project(project_id)
        self.refresh_dashboard()

    # ===========================
    # Open Folder
    # ===========================

    def open_project_folder(self, project_id):

        folder_path = db.get_project_folder(project_id)

        if folder_path and os.path.exists(folder_path):
            os.startfile(folder_path)

    def choose_ide_popup(self, ides):

        popup = ctk.CTkToplevel(self)
        popup.title("Select IDE")
        popup.geometry("350x320")
        popup.resizable(False, False)

        popup.grab_set()
        popup.focus()

        selected = {"exe": None}

        title = ctk.CTkLabel(
            popup,
            text="Choose an IDE",
            font=("Segoe UI", 22, "bold")
        )
        title.pack(pady=(20, 10))

        subtitle = ctk.CTkLabel(
            popup,
            text="Select the IDE to launch this project",
            text_color="gray"
        )
        subtitle.pack(pady=(0, 15))

        def choose(name):
            selected["exe"] = ides[name]

            db.save_ide_path(name, ides[name])

            popup.destroy()

        for name in ides.keys():
            ctk.CTkButton(
                popup,
                text=name,
                height=40,
                command=lambda n=name: choose(n)
            ).pack(fill="x", padx=30, pady=6)

        popup.wait_window()

        return selected["exe"]

    # ===========================
    # Launch Project
    # ===========================

    def launch_project(self, project_id):

        project = db.get_project(project_id)

        if not project:
            return

        folder = project[5]
        preferred = project[6]

        exe = db.get_ide_path(preferred)

        if exe is None:

            ides = self.detect_ides()

            if not ides:
                popup = ctk.CTkToplevel(self)
                popup.title("No IDE Found")
                popup.geometry("350x150")

                ctk.CTkLabel(
                    popup,
                    text="No supported IDEs were detected.",
                    font=("Segoe UI", 15)
                ).pack(expand=True)

                return

            exe = self.choose_ide_popup(ides)

            if exe is None:
                return

        try:

            subprocess.Popen([exe, folder])

        except Exception as e:

            popup = ctk.CTkToplevel(self)
            popup.title("Launch Error")
            popup.geometry("450x180")

            ctk.CTkLabel(
                popup,
                text=str(e),
                wraplength=400
            ).pack(expand=True)