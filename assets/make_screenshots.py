"""Retakes the README screenshots from the real HexDex app, filled with made-up sample Pokémon.

Writes docs/images/<view>-light.png and <view>-dark.png for the collection and detail views,
1600 x 1000 px drawn at 2x.

Run from the repository root with the project's virtual environment:
  python assets/make_screenshots.py

The sample files, nicknames, trainer names, notes and folder path below are all made up.
Settings, notes and the PokéAPI cache are kept in Meta/screenshot-cache/, never in cache/,
so no real collection data loads. The first run downloads public species, move and artwork
data from PokéAPI for the sample species (only their ID numbers are sent). Later runs are offline.
"""

import os
import struct
import sys
import tempfile
import threading
from pathlib import Path

# Draw at exactly 2x, whatever the display scaling of this computer is.
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
os.environ["QT_SCALE_FACTOR"] = "2"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as hexdex  # noqa: E402
from PyQt6.QtCore import QEventLoop, QTimer, QUrl  # noqa: E402
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

# ---- Screenshot settings ----
VERSION_LABEL = "v2.0.0"  # Newest release tag. Shown only in screenshots, never set in the source.
FAKE_FOLDER = r"C:\Users\Alex\Documents\PKHeX\Exports"
WIDTH, HEIGHT = 1600, 1000
DETAIL_SPECIES = "Charizard"
OUT_DIR = ROOT / "docs" / "images"
DEMO_CACHE = ROOT / "Meta" / "screenshot-cache"
# ------------------------------

# (generation, file name, species, level, nickname, trainer, game id, moves, gender, shiny, egg)
# Gender: 0 male, 1 female, 2 genderless. Game ids: Gen 4 7 HeartGold, 8 SoulSilver, 10 Diamond,
# 11 Pearl, 12 Platinum; Gen 6 24 X, 25 Y, 26 Alpha Sapphire, 27 Omega Ruby.
SAMPLES = [
    (4, "001 - Bulbasaur - 3A7C.pk4", 1, 14, "Sprout", "Alex", 7, (33, 45, 22, 73), 1, False, False),
    (4, "006 - Charizard - 9E21.pk4", 6, 62, "Blaze", "Alex", 8, (53, 19, 337, 89), 0, True, False),
    (4, "006 - Charizard - 51D0.pk4", 6, 48, "Ember", "Mira", 12, (52, 17, 163, 83), 1, False, False),
    (4, "025 - Pikachu - 7B44.pk4", 25, 34, "Volt", "Alex", 7, (85, 98, 86, 21), 0, False, False),
    (4, "059 - Arcanine - 0C9F.pk4", 59, 55, "Rex", "Alex", 8, (53, 245, 44, 36), 0, False, False),
    (4, "094 - Gengar - E301.pk4", 94, 58, "Haunter", "Jun", 10, (247, 94, 95, 138), 1, False, False),
    (4, "130 - Gyarados - 2D8A.pk4", 130, 48, "Tide", "Alex", 11, (127, 82, 44, 349), 0, True, False),
    (4, "131 - Lapras - 6F12.pk4", 131, 40, "Ferry", "Mira", 12, (58, 57, 47, 34), 1, False, False),
    (4, "133 - Eevee - 44B0.pk4", 133, 1, "Eevee", "Alex", 7, (33, 39, 0, 0), 0, False, True),
    (4, "143 - Snorlax - A9C3.pk4", 143, 50, "Nap", "Jun", 10, (34, 156, 173, 89), 0, False, False),
    (4, "149 - Dragonite - 1E77.pk4", 149, 64, "Atlas", "Alex", 8, (200, 349, 89, 245), 0, False, False),
    (4, "150 - Mewtwo - C0DE.pk4", 150, 70, "Mewtwo", "Alex", 8, (94, 105, 248, 133), 2, False, False),
    (4, "197 - Umbreon - 8A10.pk4", 197, 44, "Luna", "Mira", 7, (236, 44, 98, 109), 1, False, False),
    (4, "248 - Tyranitar - 5F3E.pk4", 248, 55, "Boulder", "Alex", 7, (444, 242, 89, 349), 0, False, False),
    (4, "249 - Lugia - 0A49.pk4", 249, 45, "Lugia", "Alex", 8, (177, 105, 56, 248), 2, False, False),
    (4, "282 - Gardevoir - 3C5D.pk4", 282, 41, "Grace", "Jun", 11, (94, 100, 104, 95), 1, False, False),
    (4, "393 - Piplup - D002.pk4", 393, 16, "Pip", "Alex", 12, (145, 45, 64, 55), 0, False, False),
    (4, "445 - Garchomp - 7710.pk4", 445, 66, "Mach", "Alex", 12, (200, 89, 337, 444), 0, False, False),
    (4, "448 - Lucario - B6A2.pk4", 448, 48, "Aura", "Mira", 10, (396, 370, 245, 14), 0, False, False),
    (6, "658 - Greninja - 2F6D91A0C1B3.pk6", 658, 60, "Kage", "Alex", 24, (594, 399, 58, 369), 0, False, False),
    (6, "661 - Fletchling - 81E4C02A77D0.pk6", 661, 9, "Robin", "Alex", 25, (33, 45, 64, 0), 1, False, False),
    (6, "681 - Aegislash - 4B30E9D1F2A6.pk6", 681, 52, "Excalibur", "Jun", 24, (588, 421, 14, 425), 0, False, False),
    (6, "700 - Sylveon - 9D17A64B0E52.pk6", 700, 42, "Ribbon", "Mira", 26, (585, 129, 273, 204), 1, False, False),
    (6, "704 - Goomy - C2A8F1306B9E.pk6", 704, 22, "Gloop", "Alex", 27, (55, 33, 71, 151), 1, False, False),
    (6, "716 - Xerneas - 07F2B9E4D1C3.pk6", 716, 50, "Xerneas", "Alex", 24, (585, 601, 94, 105), 2, False, False),
]

NOTES = {
    "006 - Charizard - 9E21.pk4": {
        "note": "Shiny from the Safari Zone hunt. Keep for the living dex.",
        "tags": ["Shiny hunt", "Living dex"],
        "favourite": True,
    },
    "130 - Gyarados - 2D8A.pk4": {"note": "", "tags": ["Shiny hunt"], "favourite": True},
    "445 - Garchomp - 7710.pk4": {"note": "", "tags": ["Competitive"], "favourite": True},
    "448 - Lucario - B6A2.pk4": {"note": "", "tags": ["Competitive"], "favourite": False},
    "658 - Greninja - 2F6D91A0C1B3.pk6": {"note": "", "tags": ["Competitive"], "favourite": True},
    "150 - Mewtwo - C0DE.pk4": {"note": "", "tags": ["Living dex"], "favourite": False},
}

TRAINER_ID, SECRET_ID = 24816, 13579
EVS = bytes([6, 252, 0, 252, 0, 0])


def pack_ivs(values, egg=False):
    hp, atk, de, spe, spa, spd = values
    word = hp | atk << 5 | de << 10 | spe << 15 | spa << 20 | spd << 25
    return word | (1 << 30 if egg else 0)


def gen4_name(text, length):
    """Gen 4 character set: letters only, which is all the sample names use."""
    codes = [(0x012B + ord(c) - 65) if c.isupper() else (0x0145 + ord(c) - 97) for c in text]
    codes = (codes + [0xFFFF] + [0] * length)[:length]
    return struct.pack(f"<{length}H", *codes)


def utf16_name(text, length):
    codes = ([ord(c) for c in text] + [0] * length)[:length]
    return struct.pack(f"<{length}H", *codes)


def personality(file_name, shiny):
    """A made-up PID. Shiny ones satisfy TID ^ SID ^ PID-high ^ PID-low < 8."""
    low = sum(map(ord, file_name)) * 97 & 0xFFFF
    high = (TRAINER_ID ^ SECRET_ID ^ low) if shiny else (low * 31 + 7) & 0xFFFF
    return high << 16 | low


def build(sample) -> bytes:
    gen, name, species, level, nickname, trainer, game, moves, gender, shiny, egg = sample
    pid = personality(name, shiny)
    ivs = pack_ivs((31, 28, 30, 31, 24, 29), egg)
    if gen == 4:  # Party format, 236 bytes.
        raw = bytearray(236)
        struct.pack_into("<IHHHHHH", raw, 0, pid, 0, 0, species, 0, TRAINER_ID, SECRET_ID)
        struct.pack_into("<I", raw, 16, 0)
        raw[20] = 70 if egg else 255
        raw[24:30] = EVS
        struct.pack_into("<4H", raw, 40, *moves)
        struct.pack_into("<4B", raw, 48, *(15 if m else 0 for m in moves))
        struct.pack_into("<I", raw, 0x38, ivs)
        raw[0x40] = gender << 1
        raw[72:72 + 22] = gen4_name(nickname, 11)
        raw[95] = game
        raw[104:104 + 16] = gen4_name(trainer, 8)
        raw[140] = level
    else:  # Gen 6 party format, 260 bytes.
        raw = bytearray(260)
        struct.pack_into("<IHHHHHH", raw, 0, pid, 0, 0, species, 0, TRAINER_ID, SECRET_ID)
        raw[20] = 255
        raw[28] = (species * 7) % 25  # Nature
        raw[0x1D] = gender << 1
        raw[30:36] = EVS
        raw[64:64 + 24] = utf16_name(nickname, 12)
        struct.pack_into("<4H", raw, 90, *moves)
        struct.pack_into("<4B", raw, 98, *(15 if m else 0 for m in moves))
        struct.pack_into("<I", raw, 116, ivs)
        raw[176:176 + 24] = utf16_name(trainer, 12)
        raw[223] = game
        raw[0xEC] = level
    return bytes(raw)


def isolate(sample_dir: Path) -> None:
    """Point HexDex at the demo cache and map the made-up folder path to the sample files."""
    (DEMO_CACHE / "images").mkdir(parents=True, exist_ok=True)
    hexdex.CACHE_DIR = str(DEMO_CACHE)
    hexdex.CACHE_FILE = str(DEMO_CACHE / "pokeapi_cache.json")
    hexdex.IMAGE_DIR = str(DEMO_CACHE / "images")
    hexdex.NOTES_FILE = str(DEMO_CACHE / "notes.json")
    hexdex.LAST_DIR_FILE = str(DEMO_CACHE / "last_dir.txt")
    hexdex.save_notes(NOTES)
    Path(hexdex.LAST_DIR_FILE).write_text(FAKE_FOLDER, encoding="utf-8")
    hexdex.load_build_version = lambda: VERSION_LABEL

    fake = FAKE_FOLDER.replace("/", os.sep)
    real_isdir, real_scan = os.path.isdir, hexdex.scan_directory
    os.path.isdir = lambda p: True if p == fake else real_isdir(p)
    hexdex.scan_directory = lambda d, r=False: real_scan(str(sample_dir) if d == fake else d, r)


class Browser:
    def __init__(self, url: str):
        self.view = QWebEngineView()
        self.view.resize(WIDTH, HEIGHT)
        self.view.show()
        def load(done):
            # Connect first, then load, so the wait ends when this page finishes loading.
            self.view.loadFinished.connect(lambda _ok: done())
            self.view.load(QUrl(url))

        self.wait_for(load)
        if not self.js("typeof scanDirectory === 'function'"):
            sys.exit(f"HexDex did not load at {url}")

    @staticmethod
    def wait_for(hook, timeout_ms=60000):
        loop = QEventLoop()
        hook(loop.quit)
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()

    def js(self, code: str):
        result = {}

        def run(done):
            def got(value):
                result["value"] = value
                done()
            self.view.page().runJavaScript(code, got)

        self.wait_for(run)
        return result.get("value")

    def until(self, condition: str, timeout_s=600):
        for tick in range(timeout_s * 4):
            if self.js(condition):
                return
            if tick % 40 == 39:  # Every 10 s, show what the app is doing.
                progress = hexdex.SCAN_PROGRESS
                print(f"  waiting... {progress.get('completed', 0)}/{progress.get('total', 0)} files read", flush=True)
            self.wait_for(lambda done: QTimer.singleShot(250, done))
        sys.exit(f"Timed out waiting for: {condition}")

    def settle(self, ms=800):
        self.wait_for(lambda done: QTimer.singleShot(ms, done))

    def save(self, path: Path):
        self.view.grab().save(str(path))
        print(f"Wrote {path.relative_to(ROOT)}")


THEME_JS = """
(function (theme) {
  for (const sheet of document.styleSheets) {
    const rules = sheet.cssRules;
    for (let i = rules.length - 1; i >= 0; i--) {
      const rule = rules[i];
      if (rule.media && rule.media.mediaText.includes('prefers-color-scheme')) {
        const inner = Array.from(rule.cssRules).map(r => r.cssText);
        sheet.deleteRule(i);
        if (theme === 'light') inner.forEach(text => sheet.insertRule(text, sheet.cssRules.length));
      }
    }
  }
})('%s');
"""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="hexdex-samples-") as temp:
        sample_dir = Path(temp)
        for sample in SAMPLES:
            (sample_dir / sample[1]).write_bytes(build(sample))
        isolate(sample_dir)

        server = make_server("127.0.0.1", 0, hexdex.app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/"

        qt = QApplication(sys.argv[:1])  # noqa: F841
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for theme in ("dark", "light"):
            print(f"{theme.capitalize()} theme: loading and scanning {len(SAMPLES)} sample files", flush=True)
            browser = Browser(url)
            browser.js(THEME_JS % theme)
            browser.js(f"document.getElementById('dirInput').value = {FAKE_FOLDER!r}; scanDirectory();")
            browser.settle(500)
            browser.until("!scanBusy")
            cards = browser.js("document.querySelectorAll('[onclick^=\"cardClicked\"]').length")
            if not cards:
                sys.exit("The scan loaded no Pokémon. Check the sample files with the parsers.")
            print(f"  {cards} cards shown", flush=True)
            browser.until("Array.from(document.images).every(i => i.complete)")
            browser.settle()
            browser.save(OUT_DIR / f"collection-{theme}.png")

            browser.js(
                "Array.from(document.querySelectorAll('[onclick^=\"cardClicked\"]'))"
                f".find(c => c.textContent.includes({DETAIL_SPECIES!r})).click();"
            )
            browser.settle(600)
            browser.until("Array.from(document.images).every(i => i.complete)")
            browser.settle()
            browser.save(OUT_DIR / f"detail-{theme}.png")
            browser.view.close()
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
