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

import threading
import time
import webbrowser
import app as flask_app

PORT = 5000

def run_flask():
    """Start Flask in a background thread with no reloader."""
    flask_app.app.run(port=PORT, debug=False, use_reloader=False)

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
    webview.start(gui='qt')
