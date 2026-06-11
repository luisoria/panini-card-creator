"""Prueba de renderizado de texto (sin face swap) para calibrar el layout.

Uso:  python scripts/test_render.py [equipo]
Genera assets/templates/_test_render.png con los datos de ejemplo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from app import config
from app.services import pipeline, text_renderer

SAMPLE = {
    "name": "Luis Díaz",
    "birth_date": "13-1-1997",
    "height": "1,80 m",
    "weight": "70 kg",
    "club": "FC Bayern München (GER)",
}


def main():
    team = sys.argv[1] if len(sys.argv) > 1 else "colombia"
    meta = pipeline.load_templates_meta()
    img = Image.open(config.TEMPLATES_DIR / meta[team]["file"]).convert("RGB")
    img = text_renderer.render_card_text(img, SAMPLE, meta[team]["layout"])
    out = config.TEMPLATES_DIR / "_test_render.png"
    img.save(out)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
