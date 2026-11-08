"""Tests for the manual update check, with the GitHub request stubbed (no network)."""
import os
import sys
import unittest

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import update_check as uc  # noqa: E402

SAMPLE = {"tag_name": "v2.5.0", "html_url": "https://github.com/TariqMK/HexDex/releases/tag/v2.5.0",
          "body": "- New things"}


class FakeResponse:
    def __init__(self, status, payload=None, bad_json=False):
        self.status_code, self._payload, self._bad = status, payload, bad_json

    def json(self):
        if self._bad:
            raise ValueError("bad json")
        return self._payload


def stub(response=None, error=None):
    calls = []

    def get(url, headers, timeout):
        calls.append((url, headers, timeout))
        if error:
            raise error
        return response
    return get, calls


class VersionTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(uc.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(uc.parse_version("1.2.3"), (1, 2, 3))
        for text in ("Development build", "Unknown build", "v1.2", "v1.2.3-beta", "", None):
            self.assertIsNone(uc.parse_version(text))

    def test_numeric_compare(self):
        r = uc.build_result("v0.9.0", {"tag_name": "v0.10.0", "html_url": SAMPLE["html_url"]})
        self.assertEqual(r["status"], "newer")

    def test_newer(self):
        r = uc.build_result("v2.4.0", SAMPLE)
        self.assertEqual(r["status"], "newer")
        self.assertEqual(r["headline"], "HexDex v2.5.0 is available.")
        self.assertEqual(r["detail"], "You have v2.4.0. Open the release page to download the new version.")
        self.assertEqual(r["url"], SAMPLE["html_url"])
        self.assertEqual(r["notes"], "- New things")

    def test_up_to_date(self):
        for current in ("v2.5.0", "v2.6.0"):
            r = uc.build_result(current, SAMPLE)
            self.assertEqual(r["status"], "current")
            self.assertEqual(r["headline"], "HexDex is up to date.")
            self.assertIsNone(r["url"])
        self.assertEqual(uc.build_result("v2.5.0", SAMPLE)["detail"], "v2.5.0 is the latest release.")

    def test_dev_build(self):
        r = uc.build_result("Development build", SAMPLE)
        self.assertEqual(r["status"], "dev")
        self.assertEqual(r["headline"], "This is a development build.")
        self.assertIn("The latest release is v2.5.0.", r["detail"])
        self.assertEqual(r["url"], SAMPLE["html_url"])

    def test_url_fallback(self):
        for url in (None, "", "http://example.com", "javascript:alert(1)", 5):
            r = uc.build_result("v1.0.0", {"tag_name": "v2.0.0", "html_url": url})
            self.assertEqual(r["url"], "https://github.com/TariqMK/HexDex/releases")

    def test_odd_tag(self):
        for release in ({"tag_name": "nightly"}, {}, [], "text"):
            with self.assertRaisesRegex(uc.UpdateCheckError, "can't read"):
                uc.build_result("v1.0.0", release)


class FetchTests(unittest.TestCase):
    def test_request_shape(self):
        get, calls = stub(FakeResponse(200, SAMPLE))
        self.assertEqual(uc.fetch_latest_release("v2.4.0", get=get)["status"], "newer")
        url, headers, timeout = calls[0]
        self.assertEqual(url, "https://api.github.com/repos/TariqMK/HexDex/releases/latest")
        self.assertEqual(headers, {"User-Agent": "HexDex/v2.4.0", "Accept": "application/vnd.github+json"})
        self.assertEqual(timeout, 10)

    def assertMessage(self, get, message):
        with self.assertRaises(uc.UpdateCheckError) as ctx:
            uc.fetch_latest_release("v1.0.0", get=get)
        self.assertEqual(str(ctx.exception), message)

    def test_errors(self):
        self.assertMessage(stub(FakeResponse(404))[0], "No HexDex releases are published yet.")
        for status in (403, 429):
            self.assertMessage(stub(FakeResponse(status))[0],
                               "GitHub limits how often it can be checked. Try again in an hour.")
        self.assertMessage(stub(FakeResponse(500))[0], "GitHub answered with error 500. Try again later.")
        self.assertMessage(stub(FakeResponse(200, bad_json=True))[0],
                           "GitHub sent an answer HexDex can't read. Try again later.")
        self.assertMessage(stub(error=requests.ConnectionError("x"))[0],
                           "Can't reach GitHub: no connection. Check the internet connection.")
        self.assertMessage(stub(error=requests.Timeout("x"))[0],
                           "Can't reach GitHub: the request timed out. Check the internet connection.")


if __name__ == "__main__":
    unittest.main()
