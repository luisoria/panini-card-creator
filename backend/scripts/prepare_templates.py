"""Prepara las plantillas desde la carpeta 'Template of image':

1. Convierte cada .webp a PNG y lo guarda en assets/templates/raw/<equipo>.png
2. Borra el texto original de las píldoras (nombre, datos, club) rellenando
   con el color plano de la propia píldora (mediana de los píxeles no-blancos
   de la zona), dejando la plantilla limpia en assets/templates/<equipo>.png

Uso:  python scripts/prepare_templates.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

BACKEND = Path(__file__).resolve().parent.parent
SOURCE = BACKEND.parent / "Template of image"
RAW = BACKEND / "assets" / "templates" / "raw"
OUT = BACKEND / "assets" / "templates"

PREFIX = "panini-paquete-de-inicio-de-la-copa-mundial-de-la-fifa--2026--album-----tarjetas-coleccionables-4-sobres"

# Identificado visualmente: (1)=España, (2)=Marruecos, (3)=Brasil, (4)=Colombia, base=Portugal
FILES = {
    f"{PREFIX} (1).webp": "espana",
    f"{PREFIX} (2).webp": "marruecos",
    f"{PREFIX} (3).webp": "brasil",
    f"{PREFIX} (4).webp": "colombia",
    f"{PREFIX}.webp": "portugal",
    "venezuela.png": "venezuela",
    "venezuela.webp": "venezuela",
    "venezuela.jpg": "venezuela",
}

# Zonas de texto a borrar, en fracciones (x0, y0, x1, y1) del tamaño de la imagen.
# Quedan DENTRO de las píldoras para muestrear su color plano.
# Altura casi completa de cada píldora; en X nos quedamos en la zona plana
# (después del radio de la esquina) para no comernos los bordes redondeados.
TEXT_ZONES = [
    (0.235, 0.808, 0.655, 0.893),  # nombre + línea de datos (píldora grande)
    (0.210, 0.910, 0.605, 0.950),  # club (franja inferior, a la izq. del logo)
]

# Layouts que no siguen el patrón estándar (fracciones propias por equipo)
TEAM_ZONES = {
    "venezuela": [
        # Medido sobre los píxeles blancos del texto original (ver historial)
        (0.150, 0.796, 0.700, 0.844),  # fila del nombre
        (0.105, 0.845, 0.760, 0.889),  # fila de datos (más ancha)
        (0.130, 0.905, 0.625, 0.954),  # franja inferior (antes del logo)
    ],
}


def erase_zone(arr: np.ndarray, zone: tuple) -> None:
    h, w = arr.shape[:2]
    x0, y0, x1, y1 = (int(zone[0] * w), int(zone[1] * h),
                      int(zone[2] * w), int(zone[3] * h))
    patch = arr[y0:y1, x0:x1].reshape(-1, 3).astype(np.int16)
    # El texto es blanco: excluirlo y quedarnos con el color de la píldora
    not_white = np.abs(patch - 255).sum(axis=1) > 90
    pill_pixels = patch[not_white] if not_white.any() else patch
    color = np.median(pill_pixels, axis=0).astype(np.uint8)
    arr[y0:y1, x0:x1] = color


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for fname, team in FILES.items():
        src = SOURCE / fname
        if not src.exists():
            print(f"[SKIP] no existe: {src.name}")
            continue
        img = Image.open(src).convert("RGB")
        img.save(RAW / f"{team}.png")

        arr = np.array(img)
        for zone in TEAM_ZONES.get(team, TEXT_ZONES):
            erase_zone(arr, zone)
        Image.fromarray(arr).save(OUT / f"{team}.png")
        print(f"[OK] {team}: raw + limpia ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
