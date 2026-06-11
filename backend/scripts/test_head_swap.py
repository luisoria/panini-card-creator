"""Prueba local del head swap: usa una tarjeta cruda como 'foto de usuario'.

Uso: python scripts/test_head_swap.py [template] [foto]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from app import config
from app.services import head_swap

template = sys.argv[1] if len(sys.argv) > 1 else "colombia"
photo = sys.argv[2] if len(sys.argv) > 2 else str(config.TEMPLATES_DIR / "raw" / "brasil.png")

t = cv2.imread(str(config.TEMPLATES_DIR / f"{template}.png"))
u = cv2.imread(photo)
out = head_swap.swap_head(t, u)
dest = config.TEMPLATES_DIR / "_head_swap_test.png"
cv2.imwrite(str(dest), out)
print(f"OK -> {dest}")
