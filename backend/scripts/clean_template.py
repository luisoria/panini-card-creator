"""Limpieza one-shot de una plantilla: borra los textos originales por inpainting.

Uso:
    python scripts/clean_template.py <plantilla.png> <mascara.png> <salida.png>

La máscara es una imagen del MISMO tamaño que la plantilla: negra, con las zonas
de texto a borrar pintadas en BLANCO (píntala en cualquier editor de imágenes).
Como las píldoras de texto son de color plano, el inpainting TELEA las deja
perfectamente lisas, listas para re-escribir los datos nuevos.
"""
import sys

import cv2


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    src_path, mask_path, out_path = sys.argv[1:4]
    img = cv2.imread(src_path, cv2.IMREAD_COLOR)
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if img is None or mask is None:
        sys.exit("No se pudo leer la plantilla o la máscara.")
    if img.shape[:2] != mask.shape[:2]:
        sys.exit(f"Tamaños distintos: plantilla {img.shape[:2]} vs máscara {mask.shape[:2]}")

    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    # Dilatar un poco la máscara para cubrir el antialiasing del texto
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

    clean = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    cv2.imwrite(out_path, clean)
    print(f"Plantilla limpia guardada en: {out_path}")


if __name__ == "__main__":
    main()
