"""
HexDex — Desktop Window Launcher
===================================
Run this instead of app.py to open HexDex in its own desktop window
rather than in a browser tab.

Requirements:
    pip install pywebview

Usage:
    python launch.py
    (or double-click launch.bat if you have one set up)
"""

import sys
import threading
import time
import webbrowser
from pathlib import Path

import app as flask_app

PORT = 5000
# Window and taskbar icon. PyInstaller bundles it inside the app folder;
# from source it is read from assets/icons/.
_BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ICON = _BUNDLE_DIR / ("hexdex_icon.png" if hasattr(sys, "_MEIPASS") else "assets/icons/hexdex_icon.png")

def run_flask():
    """Start Flask in a background thread with no reloader."""
    flask_app.app.run(port=PORT, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    # Start Flask in a background daemon thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # Give Flask a moment to start
    time.sleep(0.8)

    import webview
    webview.create_window(
        title="HexDex",
        url=f"http://localhost:{PORT}",
        width=1280,
        height=820,
        min_size=(900, 600),
        resizable=True,
    )
    webview.start(gui='qt', icon=str(ICON) if ICON.is_file() else None)
