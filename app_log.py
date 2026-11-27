"""HexDex log file: one always-on HexDex.log in HexDex-data that trims itself, plus View Logs.

The log never leaves the computer. It holds no file contents, typed text or network responses,
and the home folder is written as ~.
"""
import atexit
import faulthandler
import locale
import logging
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

LOG_NAME = "HexDex.log"
MAX_BYTES = 1_000_000
KEEP_BYTES = 500_000
SEPARATOR = "=" * 72
SESSION_START = "Session started"
SESSION_END = "Session ended"
TRIM_MARKER = b"--- older entries removed ---\n"

log = logging.getLogger("hexdex")
_state = {"path": None, "handler": None, "ended": False, "fault_file": None}


class TrimmedFileHandler(logging.FileHandler):
    """One log file that drops its oldest lines when it grows past max_bytes."""

    def __init__(self, path, max_bytes=MAX_BYTES, keep_bytes=KEEP_BYTES):
        super().__init__(path, encoding="utf-8")
        self.max_bytes, self.keep_bytes = max_bytes, keep_bytes
        self._trim()

    def emit(self, record):
        super().emit(record)
        try:
            if self.stream and os.fstat(self.stream.fileno()).st_size > self.max_bytes:
                self._trim()
        except OSError:
            pass

    def _trim(self):
        if self.stream:
            self.stream.close()
        path = Path(self.baseFilename)
        if path.exists() and path.stat().st_size > self.max_bytes:
            tail = path.read_bytes()[-self.keep_bytes:]
            tail = tail[tail.find(b"\n") + 1:]
            path.write_bytes(TRIM_MARKER + tail)
        self.stream = self._open()


def home_pattern(home=None):
    """Regex that matches the home folder with either slash direction, ignoring case."""
    home = str(home or Path.home()).rstrip("\\/")
    parts = [re.escape(p) for p in re.split(r"[\\/]", home)]
    return re.compile(r"[\\/]".join(parts), re.IGNORECASE)


class PrivateFormatter(logging.Formatter):
    """Format as usual, then show the home folder as ~ in the whole text, tracebacks included."""

    def __init__(self, home=None):
        super().__init__("%(asctime)s %(utc)s %(levelname)-7s [%(area)s] %(message)s")
        self.home = home_pattern(home)

    def formatTime(self, record, datefmt=None):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        return f"{stamp}.{int(record.msecs):03d}"

    def format(self, record):
        offset = time.strftime("%z", time.localtime(record.created)) or "+0000"
        record.utc = f"{offset[:3]}:{offset[3:]}"
        name = record.name
        record.area = name.split(".", 1)[1] if name.startswith("hexdex.") else ("app" if name == "hexdex" else name)
        return self.home.sub("~", super().format(record))


def private(text):
    """Show the home folder as ~ in text that is logged or shown outside the formatter."""
    return home_pattern().sub("~", str(text))


def previous_session_ended(path):
    """False when the last session in the file has no 'Session ended' line, so it crashed or was force quit."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    start = text.rfind(SESSION_START)
    if start == -1:
        return True
    return SESSION_END in text[start:]


def header_lines(version, frozen, data_dir):
    """Describe this session: app, build, system, runtime, locale and data folder."""
    if version.startswith("v"):
        kind = "release"
    elif version == "Development build":
        kind = "development"
    else:
        kind = "unknown"
    lines = [
        f"HexDex {version} ({kind} build, {'built app' if frozen else 'from source'})",
        f"System: {os_description()}, {platform.machine() or 'unknown CPU'}",
        f"Python {platform.python_version()}, Qt {qt_version()}, pywebview {package_version('pywebview')}, "
        f"Flask {package_version('flask')}",
        f"Locale: {'.'.join(filter(None, locale.getlocale())) or 'not set'}",
        f"Data folder: {data_dir}",
    ]
    return lines


def os_description():
    """Operating system name and version, e.g. 'Windows 11', 'macOS 26.1', 'Ubuntu 24.04'."""
    system = platform.system()
    if system == "Darwin":
        return f"macOS {platform.mac_ver()[0] or platform.release()}"
    if system == "Windows":
        build = sys.getwindowsversion().build if hasattr(sys, "getwindowsversion") else 0
        name = "11" if build >= 22000 else platform.release()
        return f"Windows {name}" + (f" (build {build})" if build else "")
    if system == "Linux":
        try:
            info = platform.freedesktop_os_release()
            return f"{info.get('NAME', 'Linux')} {info.get('VERSION_ID', '')}".strip()
        except OSError:
            return f"Linux {platform.release()}"
    return f"{system} {platform.release()}".strip()


def qt_version():
    try:
        from PyQt6.QtCore import QT_VERSION_STR
        return QT_VERSION_STR
    except Exception:
        return "not loaded"


def package_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "unknown"


def setup(data_dir, version, frozen):
    """Start the log file. Never raises: if the file can't be written, the app carries on without it."""
    path = Path(data_dir) / LOG_NAME
    _state["path"] = path
    if _state["handler"]:
        return path
    try:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        crashed_before = not previous_session_ended(path)
        handler = TrimmedFileHandler(path)
    except OSError as error:
        _state["error"] = str(error)
        return None
    handler.setFormatter(PrivateFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Request lines for every poll would flood the file; route errors still arrive as ERROR.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.captureWarnings(True)
    _state["handler"] = handler

    handler.stream.write(SEPARATOR + "\n")
    log.info(SESSION_START)
    for line in header_lines(version, frozen, data_dir):
        log.info(line)
    if crashed_before:
        log.warning("The previous session did not close normally (crash or force quit)")

    sys.excepthook = _log_unhandled
    threading.excepthook = lambda args: _log_unhandled(args.exc_type, args.exc_value, args.exc_traceback,
                                                       thread=args.thread.name if args.thread else "?")
    try:
        _state["fault_file"] = open(path, "a", encoding="utf-8")
        faulthandler.enable(file=_state["fault_file"])
    except (OSError, ValueError):
        pass
    atexit.register(end_session)
    return path


def _log_unhandled(exc_type, exc, tb, thread="main"):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    log.error("Unhandled error on thread %s", thread, exc_info=(exc_type, exc, tb))


def install_qt_message_handler():
    """Send Qt's own warnings and errors to the log; a windowed build has no console."""
    try:
        from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:
        return
    qt_log = logging.getLogger("hexdex.qt")
    levels = {QtMsgType.QtWarningMsg: logging.WARNING, QtMsgType.QtCriticalMsg: logging.ERROR,
              QtMsgType.QtFatalMsg: logging.ERROR}

    def handler(kind, context, message):
        level = levels.get(kind)
        if level:
            qt_log.log(level, message)

    qInstallMessageHandler(handler)


def end_session():
    """Write 'Session ended' once, when the window closes or the program exits."""
    if _state["ended"] or not _state["handler"]:
        return
    _state["ended"] = True
    log.info(SESSION_END)
    _state["handler"].flush()


def log_path():
    return _state["path"]


def reveal_command(path, system=None):
    """Command that shows the log file in the platform's file manager."""
    system = system or platform.system()
    path = str(path)
    if system == "Darwin":
        return ["open", "-R", path]
    if system == "Windows":
        return ["explorer", f"/select,{path}"]
    return ["xdg-open", os.path.dirname(path)]


def view_logs(popen=subprocess.Popen, system=None):
    """Flush the log and open the file manager at it, without a shell and without waiting.

    Returns {"ok": True} or {"ok": False, "path": ..., "error": ...} so the UI can show the path instead.
    """
    path = _state["path"]
    if path is None:
        return {"ok": False, "path": "", "error": "The log file has not been set up."}
    handler = _state["handler"]
    if handler is None:
        return {"ok": False, "path": str(path), "error": _state.get("error") or "The log file can't be written."}
    handler.flush()
    if not Path(path).is_file():
        return {"ok": False, "path": str(path), "error": "The log file is missing."}
    command = reveal_command(path, system)
    try:
        popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as error:
        log.warning("View Logs: could not run %s: %s", command[0], error)
        return {"ok": False, "path": str(path), "error": f"Could not open the file manager ({command[0]})."}
    log.info("View Logs: opened the file manager with %s", command[0])
    return {"ok": True}


def file_manager_name(system=None):
    system = system or platform.system()
    return {"Darwin": "Finder", "Windows": "File Explorer"}.get(system, "the file manager")
