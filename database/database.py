import sqlite3

class Database:

    def __init__(self):
        self.connection = sqlite3.connect("devdock.db")
        self.cursor = self.connection.cursor()

        self.create_tables()

    # ===========================
    # Create Tables
    # ===========================

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects(

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                project_name TEXT NOT NULL,

                description TEXT,

                technology TEXT,

                status TEXT,

                folder_path TEXT,

                github_url TEXT,

                live_demo TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

            )
        """)

        self.connection.commit()

    # ===========================
    # Save Project
    # ===========================

    def save_project(
        self,
        project_name,
        description,
        technology,
        status,
        folder_path,
        github_url,
        live_demo
    ):


        self.cursor.execute("""
            INSERT INTO projects(
                project_name,
                description,
                technology,
                status,
                folder_path,
                github_url,
                live_demo
            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_name,
            description,
            technology,
            status,
            folder_path,
            github_url,
            live_demo
        ))

        self.connection.commit()

    def get_projects(self):

        self.cursor.execute("""
        SELECT * 
        FROM projects
        ORDER BY id DESC                    
    """)

        return self.cursor.fetchall()
db = Database()