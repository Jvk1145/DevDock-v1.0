import sqlite3


class Database:

    def __init__(self):
        self.connection = sqlite3.connect("devdock.db")
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            description TEXT,
            technology TEXT,
            status TEXT,
            folder_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS ide_settings(
            ide_name TEXT PRIMARY KEY,
            exe_path TEXT NOT NULL
        )
        """)

        self.connection.commit()

    # -------------------------
    # Save Project
    # -------------------------

    def save_project(
        self,
        project_name,
        description,
        technology,
        status,
        folder_path
    ):

        self.cursor.execute("""
        INSERT INTO projects(
            project_name,
            description,
            technology,
            status,
            folder_path
        )
        VALUES(?,?,?,?,?)
        """,(
            project_name,
            description,
            technology,
            status,
            folder_path
        ))

        self.connection.commit()

    # -------------------------
    # Get Projects
    # -------------------------

    def get_projects(self):

        self.cursor.execute("""
        SELECT *
        FROM projects
        ORDER BY id DESC
        """)

        return self.cursor.fetchall()

    def get_project(self, project_id):

        self.cursor.execute("""
        SELECT *
        FROM projects
        WHERE id=?
        """,(project_id,))

        return self.cursor.fetchone()

    # -------------------------
    # Delete
    # -------------------------

    def delete_project(self, project_id):

        self.cursor.execute("""
        DELETE FROM projects
        WHERE id=?
        """,(project_id,))

        self.connection.commit()

    # -------------------------
    # Folder
    # -------------------------

    def get_project_folder(self, project_id):

        self.cursor.execute("""
        SELECT folder_path
        FROM projects
        WHERE id=?
        """,(project_id,))

        row=self.cursor.fetchone()

        return row[0] if row else None

    # -------------------------
    # Search
    # -------------------------

    def search_projects(self, keyword):

        self.cursor.execute("""
        SELECT *
        FROM projects
        WHERE project_name LIKE ?
        OR technology LIKE ?
        OR status LIKE ?
        ORDER BY id DESC
        """,(

            f"%{keyword}%",
            f"%{keyword}%",
            f"%{keyword}%"

        ))

        return self.cursor.fetchall()

    # -------------------------
    # IDE Settings
    # -------------------------

    def save_ide_path(self, ide_name, exe_path):

        self.cursor.execute("""
        INSERT OR REPLACE INTO ide_settings(
            ide_name,
            exe_path
        )
        VALUES(?,?)
        """,(

            ide_name,
            exe_path

        ))

        self.connection.commit()

    def get_ide_path(self, ide_name):

        self.cursor.execute("""
        SELECT exe_path
        FROM ide_settings
        WHERE ide_name=?
        """,(ide_name,))

        row=self.cursor.fetchone()

        return row[0] if row else None


db = Database()