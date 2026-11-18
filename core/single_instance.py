"""Allow only one DevDock window. A second launch asks the first one to come to the front.

* Ownership: a Windows named mutex (or an exclusive lock file elsewhere).
* Activation: the first instance listens on a random localhost port and writes
  {pid, port, token} to instance.json in the data folder. The second instance connects,
  sends the token, and exits. The token stops other local programs from poking the app.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import socket
import sys
import threading
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

ERROR_ALREADY_EXISTS = 183
ASFW_ANY = -1


class SingleInstance:
    def __init__(self, name: str, info_file: Path):
        self.name = name
        self.info_file = Path(info_file)
        self._mutex = None
        self._lock_handle = None
        self._server: socket.socket | None = None
        self._token = secrets.token_hex(16)
        self._stop = threading.Event()

    # ------------------------------------------------------------------ ownership
    def acquire(self) -> bool:
        """True if this process is the only instance."""
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
            handle = kernel32.CreateMutexW(None, False, f"Local\\{self.name}.SingleInstance")
            if not handle:
                log.warning("CreateMutexW failed; running without single-instance protection")
                return True
            if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                return False
            self._mutex = handle
            return True
        try:
            import fcntl  # type: ignore[import-not-found]
            self.info_file.parent.mkdir(parents=True, exist_ok=True)
            handle = open(self.info_file.with_suffix(".lock"), "w")
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_handle = handle
            return True
        except OSError:
            return False

    def release(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None
        try:
            data = json.loads(self.info_file.read_text(encoding="utf-8"))
            if data.get("pid") == os.getpid():
                self.info_file.unlink()
        except (OSError, ValueError):
            pass
        if self._mutex is not None:
            import ctypes
            ctypes.WinDLL("kernel32").CloseHandle(self._mutex)
            self._mutex = None
        if self._lock_handle is not None:
            self._lock_handle.close()
            self._lock_handle = None

    # ------------------------------------------------------------------ activation
    def listen(self, on_activate: Callable[[], None]) -> None:
        """Start a background listener. ``on_activate`` runs on the listener thread."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(4)
        server.settimeout(0.5)
        self._server = server
        port = server.getsockname()[1]
        self.info_file.parent.mkdir(parents=True, exist_ok=True)
        self.info_file.write_text(json.dumps({"pid": os.getpid(), "port": port, "token": self._token}),
                                  encoding="utf-8")

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    conn, _addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    try:
                        conn.settimeout(1)
                        message = conn.recv(128).decode("ascii", "ignore").strip()
                    except OSError:
                        continue
                    if message == f"ACTIVATE {self._token}":
                        log.info("Another launch asked this window to come to the front")
                        on_activate()

        threading.Thread(target=loop, name="single-instance", daemon=True).start()

    def notify_existing(self) -> bool:
        """Ask the running instance to show itself. Returns False if it could not be reached."""
        try:
            data = json.loads(self.info_file.read_text(encoding="utf-8"))
            port, token, pid = int(data["port"]), str(data["token"]), int(data["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            return False
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.WinDLL("user32").AllowSetForegroundWindow(pid)
            except (OSError, AttributeError):
                pass
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2) as conn:
                conn.sendall(f"ACTIVATE {token}\n".encode("ascii"))
            return True
        except OSError:
            return False
