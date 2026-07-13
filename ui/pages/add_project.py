import customtkinter as ctk
from tkinter import filedialog, messagebox
from database.database import db


class AddProject(ctk.CTkScrollableFrame):

    def __init__(self, parent, show_dashboard):
        self.show_dashboard = show_dashboard
        super().__init__(parent)

        self.pack(fill="both", expand=True)

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(expand=True, padx=40, pady=20)

        # -----------------------------
        # Title
        # -----------------------------

        ctk.CTkLabel(
            form_frame,
            text="Add New Project",
            font=("Segoe UI", 30, "bold")
        ).pack()

        ctk.CTkLabel(
            form_frame,
            text="Organize and manage your development projects",
            font=("Segoe UI", 14),
            text_color="gray"
        ).pack(pady=(5, 25))

        # -----------------------------
        # Project Name
        # -----------------------------

        ctk.CTkLabel(form_frame, text="Project Name").pack(anchor="w")

        self.project_name = ctk.CTkEntry(
            form_frame,
            width=650,
            height=40,
            placeholder_text="Enter Project Name"
        )

        self.project_name.pack(pady=(5, 15))

        # -----------------------------
        # Description
        # -----------------------------

        ctk.CTkLabel(form_frame, text="Description").pack(anchor="w")

        self.description = ctk.CTkTextbox(
            form_frame,
            width=650,
            height=120
        )

        self.description.pack(pady=(5, 15))

        # -----------------------------
        # Technology & Status
        # -----------------------------

        row = ctk.CTkFrame(form_frame, fg_color="transparent")
        row.pack(fill="x", pady=(5, 15))

        tech_frame = ctk.CTkFrame(row, fg_color="transparent")
        tech_frame.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(tech_frame, text="Technology").pack(anchor="w")

        self.technology = ctk.CTkComboBox(
            tech_frame,
            width=300,
            values=[
                "Python",
                "Flask",
                "Django",
                "Java",
                "C++",
                "Machine Learning",
                "Power BI"
            ]
        )

        self.technology.pack(pady=(5, 0))
        self.technology.set("Python")

        status_frame = ctk.CTkFrame(row, fg_color="transparent")
        status_frame.pack(side="left")

        ctk.CTkLabel(status_frame, text="Status").pack(anchor="w")

        self.status = ctk.CTkComboBox(
            status_frame,
            width=300,
            values=[
                "Active",
                "Completed",
                "On Hold"
            ]
        )

        self.status.pack(pady=(5, 0))
        self.status.set("Active")

        # -----------------------------
        # Project Folder
        # -----------------------------

        ctk.CTkLabel(
            form_frame,
            text="Project Folder"
        ).pack(anchor="w", pady=(10, 0))

        folder_frame = ctk.CTkFrame(
            form_frame,
            fg_color="transparent"
        )

        folder_frame.pack(fill="x", pady=(5, 20))

        self.folder = ctk.CTkEntry(
            folder_frame,
            width=500,
            height=40,
            placeholder_text="Select Project Folder"
        )

        self.folder.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            folder_frame,
            text="Browse",
            width=130,
            command=self.browse_folder
        ).pack(side="left")

        # -----------------------------
        # Buttons
        # -----------------------------

        button_frame = ctk.CTkFrame(
            form_frame,
            fg_color="transparent"
        )

        button_frame.pack(pady=20)

        ctk.CTkButton(
            button_frame,
            text="Save Project",
            width=180,
            height=42,
            command=self.save_project
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Clear Form",
            width=180,
            height=42,
            command=self.clear_form
        ).pack(side="left", padx=10)

    # ---------------------------------

    def browse_folder(self):

        folder = filedialog.askdirectory()

        if folder:
            self.folder.delete(0, "end")
            self.folder.insert(0, folder)

    # ---------------------------------

    def clear_form(self):

        self.project_name.delete(0, "end")
        self.description.delete("1.0", "end")
        self.technology.set("Python")
        self.status.set("Active")
        self.folder.delete(0, "end")

    # ---------------------------------

    def save_project(self):

        if self.project_name.get().strip() == "":
            messagebox.showwarning(
                "Validation",
                "Please enter the Project Name."
            )
            return

        if self.folder.get().strip() == "":
            messagebox.showwarning(
                "Validation",
                "Please select the Project Folder."
            )
            return

        db.save_project(
            self.project_name.get(),
            self.description.get("1.0", "end").strip(),
            self.technology.get(),
            self.status.get(),
            self.folder.get()
        )

        messagebox.showinfo(
            "Success",
            "Project Saved Successfully!"
        )

        self.clear_form()
        self.show_dashboard()