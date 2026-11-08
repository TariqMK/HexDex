"""Builds every HexDex brand image from the icon master, assets/icons/hexdex_icon.svg.

Writes:
  assets/icons/hexdex_icon.png   1024 x 1024 px
  assets/icons/hexdex_icon.ico   16-256 px, PNG-encoded (Windows exe and window)
  assets/icons/hexdex_icon.icns  16-1024 px with @2x sizes (macOS app bundle)
  docs/images/banner.png         README banner, 1280 x 320 px drawn at 2x
  docs/images/social-card.png    GitHub social preview, 1280 x 640 px

Run from the repository root with the project's virtual environment (needs PyQt6):
  python assets/make_assets.py
"""

import struct
import sys
from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QGuiApplication,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtSvg import QSvgRenderer

# ---- Brand values. Change these, then rerun the script. ----
NAME = "HexDex"
TAGLINE = "Gen 1–7 Pokémon files. One collection."
SUBLINE = "Windows · macOS · Linux"
# Colours from the app's dark theme (templates/index.html :root).
DEEP = "#0f0f10"  # --deep, darkest background
LINE = "#2a2a2c"  # --line-strong over --deep
TEXT = "#ededed"  # --text
TEXT_2 = "#a1a1a6"  # --text-2
TEXT_3 = "#85858b"  # --text-3
SANS = ["Segoe UI", "SF Pro Display", "Helvetica Neue", "Roboto", "Arial"]
MONO = ["Cascadia Mono", "SF Mono", "Consolas", "Menlo", "DejaVu Sans Mono"]
# -------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "assets" / "icons"
MASTER = ICON_DIR / "hexdex_icon.svg"
IMAGES = ROOT / "docs" / "images"

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
# ICNS chunk type -> pixel size. All chunks hold PNG data.
ICNS_TYPES = [
    ("icp4", 16), ("icp5", 32), ("icp6", 64), ("ic07", 128), ("ic08", 256),
    ("ic09", 512), ("ic10", 1024), ("ic11", 32), ("ic12", 64), ("ic13", 256), ("ic14", 512),
]


def renderer() -> QSvgRenderer:
    result = QSvgRenderer(QByteArray(MASTER.read_bytes()))
    if not result.isValid():
        sys.exit(f"Cannot read the icon master: {MASTER}")
    return result


def render_icon(svg: QSvgRenderer, size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    svg.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def write_ico(svg: QSvgRenderer, path: Path) -> None:
    images = [png_bytes(render_icon(svg, s)) for s in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, body = b"", b""
    for size, data in zip(ICO_SIZES, images):
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO format.
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        body += data
    path.write_bytes(header + entries + body)


def write_icns(svg: QSvgRenderer, path: Path) -> None:
    chunks = b""
    for kind, size in ICNS_TYPES:
        data = png_bytes(render_icon(svg, size))
        chunks += kind.encode("ascii") + struct.pack(">I", len(data) + 8) + data
    path.write_bytes(b"icns" + struct.pack(">I", len(chunks) + 8) + chunks)


def font(families: list[str], pixel_size: float, weight: QFont.Weight) -> QFont:
    available = set(QFontDatabase.families())
    result = QFont()
    result.setFamilies([f for f in families if f in available] or families)
    result.setPixelSize(round(pixel_size))
    result.setWeight(weight)
    result.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return result


def fit(base: QFont, text: str, max_width: float) -> QFont:
    """Shrink the font 2 px at a time until the text fits max_width."""
    result = QFont(base)
    while QFontMetrics(result).horizontalAdvance(text) > max_width - 8 and result.pixelSize() > 12:
        result.setPixelSize(result.pixelSize() - 2)
    if result.pixelSize() < base.pixelSize():
        print(f'Warning: "{text}" shrank from {base.pixelSize()} to {result.pixelSize()} px to fit.')
    return result


def painter_for(image: QImage) -> QPainter:
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    return painter


def write_banner(svg: QSvgRenderer, path: Path) -> None:
    """1280 x 320 rounded panel, icon left of name and tagline, centred as one group. Drawn at 2x."""
    s = 2
    width, height = 1280, 320
    image = QImage(width * s, height * s, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = painter_for(image)
    painter.scale(s, s)

    panel = QPainterPath()
    panel.addRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), 24, 24)
    painter.fillPath(panel, QColor(DEEP))
    painter.setPen(QPen(QColor(LINE), 1))
    painter.drawPath(panel)

    icon_size, gap = 176, 48
    name_font = font(SANS, 96, QFont.Weight.DemiBold)
    tag_font = fit(font(MONO, 24, QFont.Weight.Normal), TAGLINE, width - 160 - icon_size - gap)
    name_m, tag_m = QFontMetrics(name_font), QFontMetrics(tag_font)
    text_width = max(name_m.horizontalAdvance(NAME), tag_m.horizontalAdvance(TAGLINE))
    left = (width - (icon_size + gap + text_width)) / 2
    svg.render(painter, QRectF(left, (height - icon_size) / 2, icon_size, icon_size))

    # Name cap height plus a 28 px gap plus the tagline x-height block, centred vertically.
    cap, line_gap, tag_h = name_m.capHeight(), 28, tag_m.capHeight()
    top = (height - (cap + line_gap + tag_h)) / 2
    x = left + icon_size + gap
    painter.setFont(name_font)
    painter.setPen(QColor(TEXT))
    painter.drawText(QPointF(x - 96 * 0.035, top + cap), NAME)
    painter.setFont(tag_font)
    painter.setPen(QColor(TEXT_2))
    painter.drawText(QPointF(x, top + cap + line_gap + tag_h), TAGLINE)
    painter.end()
    image.save(str(path))


# Social card: GitHub repo card layout, everything 80 px inside each edge.
CARD_W, CARD_H, SAFE = 1280, 640, 80
CARD_ICON, CARD_ICON_TOP, CARD_ICON_GAP = 168, 150, 40
CARD_NAME_PX, CARD_TAGLINE_PX, CARD_TAGLINE_Y = 112, 34, 420
CARD_SUBLINE_PX, CARD_SUBLINE_Y = 24, 476


def write_social_card(svg: QSvgRenderer, path: Path) -> QImage:
    image = QImage(CARD_W, CARD_H, QImage.Format.Format_ARGB32)
    image.fill(QColor(DEEP))
    painter = painter_for(image)
    safe_width = CARD_W - 2 * SAFE

    name_font = font(SANS, CARD_NAME_PX, QFont.Weight.DemiBold)
    name_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
    icon_part = CARD_ICON + CARD_ICON_GAP
    name_font = fit(name_font, NAME, safe_width - icon_part)
    name_width = QFontMetrics(name_font).horizontalAdvance(NAME)
    left = (CARD_W - (icon_part + name_width)) / 2
    svg.render(painter, QRectF(left, CARD_ICON_TOP, CARD_ICON, CARD_ICON))
    cap = QFontMetrics(name_font).capHeight()
    painter.setFont(name_font)
    painter.setPen(QColor(TEXT))
    painter.drawText(
        QPointF(left + icon_part - name_font.pixelSize() * 0.035, CARD_ICON_TOP + CARD_ICON / 2 + cap / 2),
        NAME,
    )

    def centred(text: str, px: int, color: str, y: float) -> None:
        text_font = fit(font(MONO, px, QFont.Weight.Normal), text, safe_width)
        painter.setFont(text_font)
        painter.setPen(QColor(color))
        painter.drawText(QPointF((CARD_W - QFontMetrics(text_font).horizontalAdvance(text)) / 2, y), text)

    centred(TAGLINE, CARD_TAGLINE_PX, TEXT_2, CARD_TAGLINE_Y)
    if SUBLINE:
        centred(SUBLINE, CARD_SUBLINE_PX, TEXT_3, CARD_SUBLINE_Y)
    painter.end()
    image.save(str(path))
    return image


def check_safe_area(image: QImage) -> bool:
    background = QColor(DEEP)
    xs, ys = [], []
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y) != background:
                xs.append(x)
                ys.append(y)
    if not xs:
        print("Social card is empty")
        return False
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    print(f"Social card content: x {x0}-{x1}, y {y0}-{y1} (safe area {SAFE}-{CARD_W - SAFE}, {SAFE}-{CARD_H - SAFE})")
    return x0 >= SAFE and y0 >= SAFE and x1 <= CARD_W - SAFE and y1 <= CARD_H - SAFE


def main() -> int:
    app = QGuiApplication(sys.argv[:1])  # noqa: F841 - Qt needs an application object for fonts.
    svg = renderer()
    IMAGES.mkdir(parents=True, exist_ok=True)

    render_icon(svg, 1024).save(str(ICON_DIR / "hexdex_icon.png"))
    write_ico(svg, ICON_DIR / "hexdex_icon.ico")
    write_icns(svg, ICON_DIR / "hexdex_icon.icns")
    write_banner(svg, IMAGES / "banner.png")
    card = write_social_card(svg, IMAGES / "social-card.png")
    for name in ("icons/hexdex_icon.png", "icons/hexdex_icon.ico", "icons/hexdex_icon.icns"):
        print(f"Wrote assets/{name}")
    print("Wrote docs/images/banner.png")
    print("Wrote docs/images/social-card.png")
    if not check_safe_area(card):
        print("Social card content is outside the safe area. Shorten the tagline or subline.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
