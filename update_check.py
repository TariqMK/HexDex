"""Manual update check: asks GitHub for the latest HexDex release when the user selects the version label.

Sends one GET to the GitHub releases API. Nothing is logged, cached, downloaded or installed.
"""
import re

import requests

# ── Values to fill in by hand ──────────────────────────────────────────────
OWNER = "TariqMK"
REPO = "HexDex"
APP_NAME = "HexDex"
# ───────────────────────────────────────────────────────────────────────────

LATEST_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{OWNER}/{REPO}/releases"
TIMEOUT_SECONDS = 10

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class UpdateCheckError(Exception):
    """A failure with a message written for the user."""


def parse_version(text):
    """Return (major, minor, patch) for 'vX.Y.Z' or 'X.Y.Z', or None for anything else."""
    match = _VERSION_RE.match(str(text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def safe_release_url(url):
    """Use the release URL only when it is https; otherwise fall back to the releases page."""
    if isinstance(url, str) and url.lower().startswith("https://"):
        return url
    return RELEASES_PAGE


def build_result(current, release):
    """Turn the running version and a GitHub release object into the dialog content."""
    if not isinstance(release, dict):
        raise UpdateCheckError(f"GitHub sent an answer {APP_NAME} can't read. Try again later.")
    latest = parse_version(release.get("tag_name"))
    if latest is None:
        raise UpdateCheckError(f"GitHub sent an answer {APP_NAME} can't read. Try again later.")

    latest_text = "v{}.{}.{}".format(*latest)
    notes = release.get("body") if isinstance(release.get("body"), str) else ""
    url = safe_release_url(release.get("html_url"))
    running = parse_version(current)

    if running is None:
        return {"status": "dev", "latest": latest_text, "url": url, "notes": notes,
                "headline": "This is a development build.",
                "detail": f"You are running a development build. The latest release is {latest_text}."}
    current_text = "v{}.{}.{}".format(*running)
    if latest > running:
        return {"status": "newer", "latest": latest_text, "url": url, "notes": notes,
                "headline": f"{APP_NAME} {latest_text} is available.",
                "detail": f"You have {current_text}. Open the release page to download the new version."}
    return {"status": "current", "latest": latest_text, "url": None, "notes": "",
            "headline": f"{APP_NAME} is up to date.",
            "detail": f"{current_text} is the latest release."}


def fetch_latest_release(current, get=requests.get):
    """Ask GitHub for the latest published release. Raises UpdateCheckError with a user message."""
    headers = {"User-Agent": f"{APP_NAME}/{current}", "Accept": "application/vnd.github+json"}
    try:
        response = get(LATEST_URL, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as error:
        reason = type(error).__name__
        if isinstance(error, requests.Timeout):
            reason = "the request timed out"
        elif isinstance(error, requests.ConnectionError):
            reason = "no connection"
        raise UpdateCheckError(f"Can't reach GitHub: {reason}. Check the internet connection.") from None

    status = response.status_code
    if status == 404:
        raise UpdateCheckError(f"No {APP_NAME} releases are published yet.")
    if status in (403, 429):
        raise UpdateCheckError("GitHub limits how often it can be checked. Try again in an hour.")
    if status != 200:
        raise UpdateCheckError(f"GitHub answered with error {status}. Try again later.")
    try:
        release = response.json()
    except ValueError:
        raise UpdateCheckError(f"GitHub sent an answer {APP_NAME} can't read. Try again later.") from None
    return build_result(current, release)
