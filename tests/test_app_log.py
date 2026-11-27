"""Tests for the log file (trimming, privacy, header, crash warning, error hooks), View Logs and Report a Problem."""
import logging
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app_log  # noqa: E402


def record(msg, name="hexdex.scan", level=logging.INFO, exc_info=None):
    return logging.LogRecord(name, level, __file__, 1, msg, None, exc_info)


class TrimTests(unittest.TestCase):
    def test_trims_to_newest_whole_lines_with_marker_and_keeps_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HexDex.log"
            path.write_text("".join(f"old line {i:05d}\n" for i in range(200)), encoding="utf-8")
            handler = app_log.TrimmedFileHandler(path, max_bytes=1000, keep_bytes=300)
            handler.setFormatter(logging.Formatter("%(message)s"))
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("--- older entries removed ---\n"))
            self.assertIn("old line 00199\n", text)
            self.assertNotIn("old line 00000", text)
            self.assertTrue(text.splitlines()[1].startswith("old line "))
            for i in range(100):
                handler.emit(record(f"new line {i:05d}"))
            handler.close()
            text = path.read_text(encoding="utf-8")
            self.assertLessEqual(len(text.encode()), 1000 + 40)
            self.assertIn("new line 00099", text)

    def test_small_file_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "HexDex.log"
            path.write_text("keep me\n", encoding="utf-8")
            app_log.TrimmedFileHandler(path).close()
            self.assertEqual(path.read_text(encoding="utf-8"), "keep me\n")


class PrivacyTests(unittest.TestCase):
    def test_home_becomes_tilde_in_message_and_traceback(self):
        fmt = app_log.PrivateFormatter(home="/Users/someone")
        try:
            raise OSError("cannot open /Users/someone/Pokemon/a.pk3")
        except OSError:
            line = fmt.format(record("Reading /Users/someone/Pokemon", exc_info=sys.exc_info()))
        self.assertNotIn("/Users/someone", line)
        self.assertIn("Reading ~/Pokemon", line)
        self.assertIn("cannot open ~/Pokemon/a.pk3", line)

    def test_windows_home_both_slashes_any_case(self):
        fmt = app_log.PrivateFormatter(home=r"C:\Users\Someone")
        line = fmt.format(record(r"c:\users\someone\Pokemon and C:/Users/SOMEONE/Desktop"))
        self.assertIn(r"~\Pokemon", line)
        self.assertIn("~/Desktop", line)
        self.assertNotIn("someone", line.lower())

    def test_line_format(self):
        line = app_log.PrivateFormatter(home="/nowhere").format(record("Scan finished"))
        self.assertRegex(line, r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3} [+-]\d\d:\d\d INFO    \[scan\] Scan finished$")


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = logging.getLogger()
        self.saved = (list(self.root.handlers), self.root.level, sys.excepthook, threading.excepthook)
        app_log._state.update(path=None, handler=None, ended=False, fault_file=None)

    def tearDown(self):
        import faulthandler
        faulthandler.disable()
        handler = app_log._state["handler"]
        if handler:
            self.root.removeHandler(handler)
            handler.close()
        if app_log._state["fault_file"]:
            app_log._state["fault_file"].close()
        self.root.handlers[:], level, sys.excepthook, threading.excepthook = self.saved[0], *self.saved[1:]
        self.root.setLevel(level)
        logging.captureWarnings(False)
        app_log._state.update(path=None, handler=None, ended=False, fault_file=None)
        self.tmp.cleanup()

    def start(self, version="v3.1.0"):
        with mock.patch("atexit.register"):
            return app_log.setup(self.tmp.name, version, frozen=True)

    def test_header_has_version_build_kind_and_os(self):
        path = self.start()
        app_log.end_session()
        text = path.read_text(encoding="utf-8")
        self.assertIn("HexDex v3.1.0 (release build, built app)", text)
        self.assertIn("System: " + app_log.os_description(), text)
        self.assertIn("Session ended", text)

    def test_development_build_kind(self):
        self.assertIn("development build", app_log.header_lines("Development build", False, "/x")[0])

    def test_missing_session_end_gives_warning(self):
        Path(self.tmp.name, "HexDex.log").write_text(
            "x INFO [app] Session started\nx INFO [scan] Scan started\n", encoding="utf-8")
        path = self.start()
        self.assertIn("previous session did not close normally", path.read_text(encoding="utf-8"))

    def test_clean_previous_session_gives_no_warning(self):
        Path(self.tmp.name, "HexDex.log").write_text(
            "x INFO [app] Session started\nx INFO [app] Session ended\n", encoding="utf-8")
        path = self.start()
        self.assertNotIn("did not close normally", path.read_text(encoding="utf-8"))

    def test_unhandled_errors_reach_the_file(self):
        path = self.start()
        try:
            raise ValueError("main thread boom")
        except ValueError:
            sys.excepthook(*sys.exc_info())
        worker = threading.Thread(target=lambda: 1 / 0, name="worker")
        worker.start()
        worker.join()
        self.root.handlers[-1].flush()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Unhandled error on thread main", text)
        self.assertIn("ValueError: main thread boom", text)
        self.assertIn("Unhandled error on thread worker", text)
        self.assertIn("ZeroDivisionError", text)

    def test_view_logs_opens_file_manager_without_shell(self):
        path = self.start()
        calls = []
        result = app_log.view_logs(popen=lambda cmd, **kw: calls.append((cmd, kw)), system="Darwin")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls[0][0], ["open", "-R", str(path)])
        self.assertNotIn("shell", calls[0][1])

    def test_view_logs_failure_returns_path(self):
        path = self.start()

        def broken(cmd, **kw):
            raise FileNotFoundError(cmd[0])
        result = app_log.view_logs(popen=broken, system="Linux")
        self.assertFalse(result["ok"])
        self.assertEqual(result["path"], str(path))

    def test_unwritable_folder_does_not_raise(self):
        blocker = Path(self.tmp.name, "file")
        blocker.write_text("", encoding="utf-8")
        with mock.patch("atexit.register"):
            self.assertIsNone(app_log.setup(blocker / "sub", "v1.0.0", frozen=True))
        result = app_log.view_logs(popen=lambda *a, **k: None)
        self.assertFalse(result["ok"])
        self.assertTrue(result["path"].endswith("HexDex.log"))


class RevealCommandTests(unittest.TestCase):
    def test_platform_commands(self):
        self.assertEqual(app_log.reveal_command("/d/HexDex.log", "Darwin"), ["open", "-R", "/d/HexDex.log"])
        self.assertEqual(app_log.reveal_command(r"C:\d\HexDex.log", "Windows"), ["explorer", r"/select,C:\d\HexDex.log"])
        self.assertEqual(app_log.reveal_command("/d/HexDex.log", "Linux"), ["xdg-open", "/d"])

    def test_file_manager_names(self):
        self.assertEqual(app_log.file_manager_name("Darwin"), "Finder")
        self.assertEqual(app_log.file_manager_name("Windows"), "File Explorer")
        self.assertEqual(app_log.file_manager_name("Linux"), "the file manager")


class ReportProblemTests(unittest.TestCase):
    def setUp(self):
        import app
        self.url = app.report_problem_url

    def test_release_version_and_os_are_encoded(self):
        url = self.url("v3.0.1", "Windows 11 (build 26100)")
        self.assertEqual(url, "https://github.com/TariqMK/HexDex/issues/new?template=bug.yml"
                              "&version=3.0.1&os=Windows+11+%28build+26100%29")

    def test_development_build_goes_in_as_it_is(self):
        self.assertIn("version=Development+build", self.url("Development build", "macOS 26.1"))


if __name__ == "__main__":
    unittest.main()
