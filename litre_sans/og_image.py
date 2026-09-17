"""Images d'aperçu Open Graph (1200 x 630) générées au build avec Pillow."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
SIZE = (1200, 630)
EN_DASH = "\u2013"

BG = "#0F1A1C"
DISPLAY = "#050D0E"
PUMP = "#F2B705"
DIGITS = "#FFD34D"
INK = "#E6EEEE"
MUTED = "#93A6A8"
GOOD = "#4CC38A"
PETROL = "#5FB3BC"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS_DIR / f"{name}.ttf"), size)


def fr(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def _wrap(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_scenario(
    *,
    title: str,
    price_before: float,
    price_after: float,
    tank_saving: float,
    tank_litres: float,
    fuel_label: str,
    site_title: str,
) -> Image.Image:
    img = Image.new("RGB", SIZE, BG)
    d = ImageDraw.Draw(img)

    # Bandeau titre
    d.text((60, 44), site_title, font=_font("BarlowCondensed-Bold", 44), fill=PETROL)
    d.text(
        (60, 100),
        "Et si les économies allaient à la pompe ?",
        font=_font("Barlow-Regular", 26),
        fill=MUTED,
    )

    # Afficheur de pompe
    box = (60, 160, 1140, 470)
    d.rounded_rectangle(box, radius=18, fill=DISPLAY, outline=PUMP, width=5)
    d.text((100, 190), f"{fuel_label} — prix simulé", font=_font("Barlow-Regular", 24), fill=MUTED)
    d.text((100, 225), f"{fr(price_after)} €", font=_font("BarlowCondensed-Bold", 150), fill=DIGITS)
    d.text(
        (100, 395),
        f"Aujourd'hui : {fr(price_before)} €/L",
        font=_font("Barlow-SemiBold", 30),
        fill=INK,
    )
    saving = f"{EN_DASH}{fr(tank_saving)} € sur un plein de {fr(tank_litres, 0)} L"
    d.text((1100, 400), saving, font=_font("BarlowCondensed-Bold", 54), fill=GOOD, anchor="ra")

    # Titre du scénario
    font = _font("Barlow-SemiBold", 38)
    y = 500
    for line in _wrap(d, title, font, 1080)[:2]:
        d.text((60, y), line, font=font, fill=INK)
        y += 48
    return img
