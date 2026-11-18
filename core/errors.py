"""Custom exceptions. Every exception carries a message that is safe to show to users."""
from __future__ import annotations


class DevDockError(Exception):
    """Base error. ``user_message`` is friendly text; ``detail`` is technical text for logs."""

    title = "Something went wrong"

    def __init__(self, user_message: str, detail: str | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail or user_message


class ValidationError(DevDockError):
    title = "Please check the form"

    def __init__(self, errors: dict[str, str]):
        self.errors = dict(errors)
        first = next(iter(self.errors.values()), "Some fields are invalid.")
        super().__init__(first, "; ".join(f"{k}: {v}" for k, v in self.errors.items()))


class NotFoundError(DevDockError):
    title = "Not found"


class DatabaseError(DevDockError):
    title = "Database problem"


class DatabaseCorruptError(DatabaseError):
    title = "Database is damaged"


class ImportExportError(DevDockError):
    title = "Import / export failed"


class LaunchError(DevDockError):
    """Raised when something cannot be opened.

    ``kind`` tells the UI which fix to offer:
      folder_missing -> "Locate folder"
      ide_missing    -> "Fix IDE path"
      no_ide         -> "Open Settings"
      failed         -> generic
    """

    title = "Could not open"

    FOLDER_MISSING = "folder_missing"
    IDE_MISSING = "ide_missing"
    NO_IDE = "no_ide"
    FAILED = "failed"

    def __init__(self, user_message: str, kind: str = FAILED, detail: str | None = None,
                 ide_key: str | None = None, path: str | None = None):
        super().__init__(user_message, detail)
        self.kind = kind
        self.ide_key = ide_key
        self.path = path
