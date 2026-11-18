"""DevDock entry point: logging, DPI awareness, single instance, error handling, start UI."""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
import traceback

import config

log = logging.getLogger("devdock")


# ---------------------------------------------------------------------- bootstrap helpers
def setup_logging() -> None:
    config.ensure_dirs()
    handler = logging.handlers.RotatingFileHandler(config.LOG_FILE, maxBytes=config.LOG_MAX_BYTES,
                                                   backupCount=config.LOG_BACKUP_COUNT, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s [%(threadName)s] %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if not getattr(sys, "frozen", False) and sys.stderr is not None:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)-7s %(name)s: %(message)s"))
        console.setLevel(logging.WARNING)
        root.addHandler(console)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # per-monitor aware: sharp text
    except (OSError, AttributeError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (OSError, AttributeError):
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.APP_USER_MODEL_ID)
    except (OSError, AttributeError):
        pass


def native_message(title: str, text: str, kind: str = "error") -> None:
    """Message box that works before (or without) Tk."""
    if sys.platform == "win32":
        import ctypes
        flags = {"error": 0x10, "warning": 0x30, "info": 0x40}.get(kind, 0x40)
        ctypes.windll.user32.MessageBoxW(None, text, title, flags | 0x10000)  # MB_SETFOREGROUND
    else:
        print(f"{title}: {text}", file=sys.stderr)


class ErrorReporter:
    """Logs every unhandled exception and shows a friendly dialog. The app never closes silently."""

    def __init__(self) -> None:
        self.window = None
        self._showing = False

    def install(self) -> None:
        sys.excepthook = self.handle
        threading.excepthook = lambda args: self.handle_from_thread(args.exc_type, args.exc_value,
                                                                    args.exc_traceback)

    def handle_from_thread(self, exc_type, exc, tb) -> None:
        log.error("Unhandled exception in a background thread", exc_info=(exc_type, exc, tb))
        if self.window is not None:
            self.window.runner.post(lambda: self._show(exc_type, exc, tb, logged=True))

    def handle(self, exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            return
        self._show(exc_type, exc, tb)

    def _show(self, exc_type, exc, tb, logged: bool = False) -> None:
        from core.errors import DevDockError

        details = "".join(traceback.format_exception(exc_type, exc, tb))
        if not logged:
            log.error("Unhandled exception\n%s", details)
        if isinstance(exc, DevDockError):
            title, message = exc.title, exc.user_message
        else:
            title = "Something went wrong"
            message = "DevDock hit an unexpected problem. Your data is safe. The details were saved to the log."
        if self.window is None or self._showing:
            if self.window is None:
                native_message(title, f"{message}\n\nLog: {config.LOG_FILE}")
            return
        self._showing = True
        try:
            from ui.widgets.dialogs import ErrorDialog
            ErrorDialog(self.window, title, message, f"DevDock {config.APP_VERSION}\n{details}").show()
        except Exception:
            log.exception("The error dialog itself failed")
            native_message(title, f"{message}\n\nLog: {config.LOG_FILE}")
        finally:
            self._showing = False


# ---------------------------------------------------------------------- database
def open_database():
    """Open, verify and migrate the database. Offers recovery if it is damaged."""
    from core.database import Database
    from core.errors import DatabaseCorruptError

    db = Database(config.DB_PATH, config.BACKUP_DIR, config.BACKUPS_TO_KEEP)
    try:
        db.open()
        db.check_integrity()
        db.migrate()
    except DatabaseCorruptError as exc:
        log.error("Database is damaged: %s", exc.detail)
        db = recover_database(db)
    try:
        db.daily_backup()
    except Exception:
        log.exception("Daily backup failed")
    return db


def recover_database(db):
    from tkinter import messagebox
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        latest = db.latest_backup()
        if latest is not None:
            answer = messagebox.askyesnocancel(
                "DevDock database is damaged",
                "DevDock's database could not be read.\n\n"
                f"Yes: restore the latest backup ({latest.created:%Y-%m-%d %H:%M}).\n"
                "No: start with an empty database (the damaged file is kept).\n"
                "Cancel: quit DevDock.", icon="warning", parent=root)
        else:
            answer = False if messagebox.askokcancel(
                "DevDock database is damaged",
                "DevDock's database could not be read and there is no backup yet.\n\n"
                "OK: start with an empty database (the damaged file is kept next to it).\n"
                "Cancel: quit DevDock.", icon="warning", parent=root) else None
    finally:
        root.destroy()
    if answer is None:
        raise SystemExit(1)
    moved = db.quarantine()
    db.open()
    if answer:
        db.restore(latest.path)
        log.warning("Restored %s after corruption (damaged copy: %s)", latest.path, moved)
    else:
        db.migrate()
        log.warning("Started with a fresh database (damaged copy: %s)", moved)
    return db


def import_legacy_data(ctx) -> int:
    """First run of 2.x: merge projects from DevDock 1.x 'devdock.db' files."""
    if not ctx.db.created_new:
        return 0
    added = 0
    for path in config.legacy_db_candidates():
        try:
            result = ctx.projects.merge_legacy_database(path)
            added += result.added
        except Exception:
            log.exception("Could not import legacy database %s", path)
    return added


# ---------------------------------------------------------------------- main
def main() -> int:
    setup_logging()
    log.info("Starting %s %s (Python %s, data folder %s)", config.APP_NAME, config.APP_VERSION,
             sys.version.split()[0], config.APP_DIR)
    reporter = ErrorReporter()
    reporter.install()
    enable_dpi_awareness()

    from core.single_instance import SingleInstance

    instance = SingleInstance(config.APP_NAME, config.INSTANCE_FILE)
    if not instance.acquire():
        log.info("DevDock is already running; activating the existing window")
        if not instance.notify_existing():
            native_message(config.APP_NAME, "DevDock is already running.", "info")
        return 0

    db = None
    try:
        db = open_database()
        from ui.context import AppContext
        from ui.main_window import MainWindow

        ctx = AppContext.create(db)
        ctx.legacy_imported = import_legacy_data(ctx)
        window = MainWindow(ctx)
        reporter.window = window
        window.report_callback_exception = reporter.handle
        instance.listen(lambda: window.runner.post(window.bring_to_front))
        window.mainloop()
    except SystemExit:
        raise
    except Exception as exc:
        reporter.handle(type(exc), exc, exc.__traceback__)
        return 1
    finally:
        instance.release()
        if db is not None:
            db.close()
        log.info("DevDock closed")
        logging.shutdown()
    return 0


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
    sys.exit(main())
