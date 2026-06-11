"""Renderizado tipográfico sobre la tarjeta con Pillow.

Estilo del álbum 2026:
- Nombre:  condensed bold, MAYÚSCULAS, blanco; el apellido va más pesado
           (se simula con stroke del mismo color sobre Bebas Neue).
- Datos:   "13-1-1997 | 1,80 m | 70 kg" — condensed, separador " | ".
- Club:    "FC BAYERN MÜNCHEN (GER)" — condensed, MAYÚSCULAS, franja inferior.
Todo centrado en el eje de su zona (center_x relativo, ver templates.json).
"""
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .. import config

_FONT_FILES = {
    "name": config.FONT_NAME,
    "stats": config.FONT_STATS,
    "stats_bold": config.FONT_STATS_BOLD,
}


_VARIATIONS = {"stats": "Regular", "stats_bold": "Bold"}


@lru_cache(maxsize=32)
def _font(kind: str, px: int) -> ImageFont.FreeTypeFont:
    path = config.FONTS_DIR / _FONT_FILES[kind]
    if not path.exists():
        raise FileNotFoundError(
            f"Falta la fuente {path.name} en {config.FONTS_DIR}. Ver README (Google Fonts)."
        )
    font = ImageFont.truetype(str(path), px)
    if kind in _VARIATIONS:
        try:  # fuente variable (RobotoCondensed[wght]): fijar el peso
            font.set_variation_by_name(_VARIATIONS[kind])
        except OSError:
            pass  # fuente estática: ya tiene el peso correcto
    return font


def _draw_centered(draw, text, center_x_px, y_px, font, color, stroke=0):
    """Dibuja texto centrado horizontalmente en center_x_px, con top en y_px."""
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    x = center_x_px - (right - left) / 2 - left
    draw.text((x, y_px - top), text, font=font, fill=color,
              stroke_width=stroke, stroke_fill=color)


def _draw_name(draw, name, zone, w, h):
    """Nombre con apellido en peso mayor: 'LUIS' normal + 'DÍAZ' con stroke."""
    name = name.strip().upper()
    px = round(zone["size"] * h)
    font = _font("name", px)
    parts = name.rsplit(" ", 1)
    cx, y = zone["center_x"] * w, zone["y"] * h

    if len(parts) == 1:
        _draw_centered(draw, name, cx, y, font, zone["color"], stroke=max(1, px // 28))
        return

    first, last = parts[0] + " ", parts[1]
    bold_stroke = max(1, px // 30)
    w_first = draw.textlength(first, font=font)
    w_last = draw.textlength(last, font=font) + 2 * bold_stroke
    x0 = cx - (w_first + w_last) / 2

    top = draw.textbbox((0, 0), name, font=font)[1]
    draw.text((x0, y - top), first, font=font, fill=zone["color"])
    draw.text((x0 + w_first, y - top), last, font=font, fill=zone["color"],
              stroke_width=bold_stroke, stroke_fill=zone["color"])


def render_card_text(img: Image.Image, data: dict, layout: dict) -> Image.Image:
    """Escribe nombre, línea de datos y club sobre la tarjeta.

    data: {name, birth_date, height, weight, club}
    """
    draw = ImageDraw.Draw(img)
    w, h = img.size

    _draw_name(draw, data["name"], layout["name"], w, h)

    z = layout["stats"]
    stats_line = " | ".join([data["birth_date"], data["height"], data["weight"]])
    _draw_centered(draw, stats_line, z["center_x"] * w, z["y"] * h,
                   _font(z["font"], round(z["size"] * h)), z["color"])

    z = layout["club"]
    _draw_centered(draw, data["club"].strip().upper(), z["center_x"] * w, z["y"] * h,
                   _font(z["font"], round(z["size"] * h)), z["color"])

    return img
