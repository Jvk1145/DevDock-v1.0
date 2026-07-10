import customtkinter as ctk


class AddProject(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent)

        title = ctk.CTkLabel(
            self,
            text="Add New Project",
            font=("Segoe UI", 28, "bold")
        )
        title.pack(pady=20)

        # Project Name
        ctk.CTkLabel(self, text="Project Name").pack(anchor="w", padx=30)

        self.project_name = ctk.CTkEntry(
            self,
            width=500
        )
        self.project_name.pack(pady=10)

        # Description
        ctk.CTkLabel(self, text="Description").pack(anchor="w", padx=30)

        self.description = ctk.CTkTextbox(
            self,
            width=500,
            height=100
        )
        self.description.pack(pady=10)

        # Technology
        ctk.CTkLabel(self, text="Technology").pack(anchor="w", padx=30)

        self.technology = ctk.CTkComboBox(
            self,
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

        self.technology.pack(pady=10)

        save_btn = ctk.CTkButton(
            self,
            text="Save Project"
        )

        save_btn.pack(pady=25)