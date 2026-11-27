"""
HexDex — Desktop Window Launcher
===================================
Opens HexDex in its own desktop window (pywebview with Qt) instead of a browser tab.
It starts the Flask app in a background thread, starts the log file in HexDex-data,
and opens the window.

Usage:
    python launch.py
"""

import logging
import sys
import threading
import time
from pathlib import Path

STARTED = time.monotonic()

import app as flask_app  # noqa: E402
import app_log  # noqa: E402

PORT = 5000
# Window and taskbar icon. PyInstaller bundles it inside the app folder;
# from source it is read from assets/icons/.
_BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ICON = _BUNDLE_DIR / ("hexdex_icon.png" if hasattr(sys, "_MEIPASS") else "assets/icons/hexdex_icon.png")

log = logging.getLogger("hexdex.startup")


def run_flask():
    """Start Flask in a background thread with no reloader."""
    try:
        flask_app.app.run(port=PORT, debug=False, use_reloader=False, threaded=True)
    except Exception:
        log.error("The local server stopped or could not start on port %d", PORT, exc_info=True)
        raise


def log_screens(window):
    """Runs once the window exists: log the screens and how long startup took."""
    try:
        from PyQt6.QtGui import QGuiApplication
        screens = QGuiApplication.screens()
        log.info("Screens: %d (%s)", len(screens), ", ".join(
            f"{s.size().width()} x {s.size().height()} at {s.devicePixelRatio():g}x" for s in screens))
    except Exception as error:
        log.info("Screens: not available (%s)", error)
    log.info("Window shown %.1f s after start", time.monotonic() - STARTED)


if __name__ == "__main__":
    app_log.setup(flask_app.CACHE_DIR, flask_app.load_build_version(), getattr(sys, "frozen", False))
    if flask_app.LEGACY_COPIED:
        log.info("Copied data from the old cache folder %s into %s. The old folder was not changed.",
                 flask_app.LEGACY_CACHE_DIR, flask_app.CACHE_DIR)
    last_dir = Path(flask_app.LAST_DIR_FILE)
    log.info("Settings: last-used folder %s", "saved" if last_dir.is_file() else "not set (default)")
    for name in ("pokeapi_cache.json", "notes.json"):
        path = Path(flask_app.CACHE_DIR) / name
        log.info("%s: %s", name, f"{path.stat().st_size / 1024:.1f} KB" if path.is_file() else "not created yet")

    # Start Flask in a background daemon thread
    t = threading.Thread(target=run_flask, daemon=True, name="flask")
    t.start()
    log.info("Local server starting on port %d", PORT)

    # Give Flask a moment to start
    time.sleep(0.8)

    try:
        import webview
        app_log.install_qt_message_handler()
        window = webview.create_window(
            title="HexDex",
            url=f"http://localhost:{PORT}",
            width=1280,
            height=820,
            min_size=(900, 600),
            resizable=True,
        )
        window.events.closed += app_log.end_session
        log.info("Opening the window (pywebview %s, Qt backend)", app_log.package_version("pywebview"))
        webview.start(log_screens, window, gui='qt', icon=str(ICON) if ICON.is_file() else None)
    except Exception:
        log.error("The window could not be opened", exc_info=True)
        raise
    finally:
        app_log.end_session()
