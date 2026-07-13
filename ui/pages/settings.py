import customtkinter as ctk
from tkinter import filedialog, messagebox

from database.database import db


class Settings(ctk.CTkScrollableFrame):

    def __init__(self, parent):
        super().__init__(parent)

        self.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self,
            text="Settings",
            font=("Segoe UI", 30, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text="Configure IDE paths if they are not installed in the default location.",
            text_color="gray"
        ).pack(pady=(0, 20))

        self.ides = [
            "VS Code",
            "PyCharm",
            "Cursor",
            "Android Studio",
            "Visual Studio",
            "IntelliJ IDEA"
        ]

        self.entries = {}

        for ide in self.ides:

            ctk.CTkLabel(
                self,
                text=ide
            ).pack(anchor="w", padx=30)

            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=30, pady=(5, 15))

            entry = ctk.CTkEntry(
                row,
                width=500,
                height=40
            )

            saved = db.get_ide_path(ide)

            if saved:
                entry.insert(0, saved)

            entry.pack(side="left", padx=(0, 10))

            ctk.CTkButton(
                row,
                text="Browse",
                width=120,
                command=lambda i=ide, e=entry: self.browse(i, e)
            ).pack(side="left")

            self.entries[ide] = entry

        ctk.CTkButton(
            self,
            text="Save Settings",
            width=200,
            height=45,
            command=self.save_settings
        ).pack(pady=20)

    def browse(self, ide, entry):

        path = filedialog.askopenfilename(
            title=f"Select {ide} Executable",
            filetypes=[("Executable Files", "*.exe")]
        )

        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def save_settings(self):

        for ide, entry in self.entries.items():

            path = entry.get().strip()

            if path:
                db.save_ide_path(ide, path)

        messagebox.showinfo(
            "Success",
            "Settings Saved Successfully!"
        )