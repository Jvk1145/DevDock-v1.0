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

        title = ctk.CTkLabel(
            form_frame,
            text="Add New Project",
            font=("Segoe UI", 30, "bold")
        )
        title.pack()

        subtitle = ctk.CTkLabel(
            form_frame,
            text="Organize and manage your development projects",
            font=("Segoe UI", 14),
            text_color="gray"
        )
        subtitle.pack(pady=(5, 25))

        ctk.CTkLabel(form_frame, text="Project Name").pack(anchor="w")
        self.project_name = ctk.CTkEntry(
            form_frame,
            width=650,
            height=40,
            placeholder_text="Enter Project Name"
        )
        self.project_name.pack(pady=(5, 15))

        ctk.CTkLabel(form_frame, text="Description").pack(anchor="w")
        self.description = ctk.CTkTextbox(
            form_frame,
            width=650,
            height=120
        )
        self.description.pack(pady=(5, 15))

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
                "Power BI",
                "Machine Learning",
                "Java",
                "C++"
            ]
        )
        self.technology.pack(pady=(5, 0))

        status_frame = ctk.CTkFrame(row, fg_color="transparent")
        status_frame.pack(side="left")

        ctk.CTkLabel(status_frame, text="Status").pack(anchor="w")
        self.status = ctk.CTkComboBox(
            status_frame,
            width=300,
            values=["Active", "Completed", "On Hold"]
        )
        self.status.pack(pady=(5, 0))

        ctk.CTkLabel(form_frame, text="Project Folder").pack(anchor="w", pady=(10, 0))

        folder_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        folder_frame.pack(fill="x", pady=(5, 15))

        self.folder = ctk.CTkEntry(
            folder_frame,
            width=500,
            height=40,
            placeholder_text="Select Project Folder"
        )
        self.folder.pack(side="left", padx=(0, 10))

        browse_btn = ctk.CTkButton(
            folder_frame,
            text="Browse",
            width=130,
            command=self.browse_folder
        )
        browse_btn.pack(side="left")

        ctk.CTkLabel(form_frame, text="GitHub Repository").pack(anchor="w")
        self.github = ctk.CTkEntry(
            form_frame,
            width=650,
            height=40,
            placeholder_text="https://github.com/username/project"
        )
        self.github.pack(pady=(5, 15))

        ctk.CTkLabel(form_frame, text="Live Demo URL (Optional)").pack(anchor="w")
        self.demo = ctk.CTkEntry(
            form_frame,
            width=650,
            height=40,
            placeholder_text="https://"
        )
        self.demo.pack(pady=(5, 20))

        button_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save Project",
            width=180,
            height=42,
            command=self.save_project
        )
        save_btn.pack(
            side="left",
            padx=10
        )

        clear_btn = ctk.CTkButton(
            button_frame,
            text="Clear Form",
            width=180,
            height=42,
            command=self.clear_form
        )
        clear_btn.pack(side="left", padx=10)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.delete(0, "end")
            self.folder.insert(0, folder)

    def clear_form(self):
        self.project_name.delete(0, "end")
        self.description.delete("1.0", "end")
        self.technology.set("Python")
        self.status.set("Active")
        self.folder.delete(0, "end")
        self.github.delete(0, "end")
        self.demo.delete(0, "end")

    def save_project(self):

        # Validate Project Name
        if self.project_name.get().strip() == "":
            messagebox.showwarning(
                "Validation",
                "Please enter the Project Name."
            )
            return

        db.save_project(
            self.project_name.get(),
            self.description.get("1.0", "end").strip(),
            self.technology.get(),
            self.status.get(),
            self.folder.get(),
            self.github.get(),
            self.demo.get()
        )

        messagebox.showinfo(
            "Success",
            "Project Saved Successfully!"
        )

        self.clear_form()

        self.show_dashboard()