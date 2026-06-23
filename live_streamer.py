"""
live_streamer.py - True event-driven file watcher for Live Streaming Orders Analytics

Uses the `watchdog` library (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW
on Windows) for genuine OS-level file-system events — NOT polling.

The watcher fires only when the OS notifies that orders.csv has been modified,
making this a real event-driven streaming pipeline.
"""

import os
import sqlite3

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import db_manager


class _CSVChangeHandler(FileSystemEventHandler):
    """Handles OS file-system events; fires callback only when our CSV is modified."""

    def __init__(self, csv_path: str, db_file: str, callback) -> None:
        super().__init__()
        self.csv_path = os.path.abspath(csv_path)
        self.db_file  = db_file
        self.callback = callback

    def on_modified(self, event) -> None:
        if os.path.abspath(event.src_path) != self.csv_path:
            return  # Ignore changes to other files in the directory
        try:
            # Open a fresh connection per event (watchdog runs events in its own thread)
            conn = db_manager.get_connection(self.db_file)
            inserted = db_manager.load_data(conn, self.csv_path)
            conn.close()
            print(f"[watcher] CSV modified (inotify/FSEvents) — {inserted} new row(s) added.")
            self.callback()
        except Exception as exc:
            print(f"[watcher] Error handling event: {exc}")


class FileWatcher:
    """
    Wraps a watchdog Observer to watch a single CSV file for OS-level change events.
    Uses inotify (Linux), FSEvents (macOS), or ReadDirectoryChangesW (Windows).
    """

    def __init__(self, csv_path: str, db_file: str, callback) -> None:
        self.csv_path  = csv_path
        self.db_file   = db_file
        self.callback  = callback
        self._observer: Observer | None = None

    def start(self) -> None:
        watch_dir = os.path.dirname(os.path.abspath(self.csv_path)) or "."
        handler   = _CSVChangeHandler(self.csv_path, self.db_file, self.callback)
        self._observer = Observer()
        self._observer.schedule(handler, path=watch_dir, recursive=False)
        self._observer.start()
        print(f"[watcher] Watching {self.csv_path} via OS file-system events …")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
        print("[watcher] Stopped.")
