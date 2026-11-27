"""Tests for where HexDex keeps its data folder, and the one-time copy from the old cache folder."""
import os
import posixpath
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402


class AppFolderTests(unittest.TestCase):
    def setUp(self):
        # These cases are macOS and Linux paths. Use POSIX path rules on every system,
        # so Windows does not turn "/home/alex" into "C:\\home\\alex".
        patcher = mock.patch.object(app.os, "path", posixpath)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_source_run_uses_project_folder(self):
        self.assertEqual(app.app_folder("/usr/bin/python3", False, "/src/HexDex", "darwin"), "/src/HexDex")

    def test_macos_build_uses_folder_beside_app_bundle(self):
        exe = "/Users/alex/Apps/HexDex.app/Contents/MacOS/HexDex"
        self.assertEqual(app.app_folder(exe, True, "/unused", "darwin"), "/Users/alex/Apps")

    def test_macos_executable_outside_bundle_uses_its_folder(self):
        self.assertEqual(app.app_folder("/opt/hexdex/HexDex", True, "/unused", "darwin"), "/opt/hexdex")

    def test_linux_build_uses_executable_folder(self):
        self.assertEqual(app.app_folder("/home/alex/HexDex/HexDex", True, "/unused", "linux"), "/home/alex/HexDex")

    def test_data_folder_name(self):
        self.assertEqual(Path(app.CACHE_DIR).name, "HexDex-data")


class CopyLegacyDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.legacy = os.path.join(self.tmp.name, "cache")
        self.data = os.path.join(self.tmp.name, "HexDex-data")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_copies_old_folder_and_keeps_it(self):
        self.write(os.path.join(self.legacy, "notes.json"), '{"a.pk4": {"note": "keep"}}')
        self.write(os.path.join(self.legacy, "images", "6_hd.png"), "png")
        self.assertTrue(app.copy_legacy_data(self.legacy, self.data))
        with open(os.path.join(self.data, "notes.json"), encoding="utf-8") as f:
            self.assertIn("keep", f.read())
        self.assertTrue(os.path.exists(os.path.join(self.data, "images", "6_hd.png")))
        self.assertTrue(os.path.exists(os.path.join(self.legacy, "notes.json")))

    def test_never_overwrites_existing_data_folder(self):
        self.write(os.path.join(self.legacy, "notes.json"), "old")
        self.write(os.path.join(self.data, "notes.json"), "new")
        self.assertFalse(app.copy_legacy_data(self.legacy, self.data))
        with open(os.path.join(self.data, "notes.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "new")

    def test_nothing_to_copy(self):
        self.assertFalse(app.copy_legacy_data(self.legacy, self.data))
        self.assertFalse(os.path.exists(self.data))


if __name__ == "__main__":
    unittest.main()
