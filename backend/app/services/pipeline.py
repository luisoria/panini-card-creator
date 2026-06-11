"""Orquestación: plantilla limpia -> face swap -> texto -> PNG final."""
import io
import json
import os
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

from .. import config
from . import face_swap, text_renderer


@lru_cache(maxsize=1)
def load_templates_meta() -> dict:
    with open(config.TEMPLATES_META, encoding="utf-8") as f:
        meta = json.load(f)
    meta.pop("_doc", None)
    return meta


def list_teams() -> list[dict]:
    meta = load_templates_meta()
    return [
        {
            "id": team_id,
            "name": t["display_name"],
            "available": (config.TEMPLATES_DIR / t["file"]).exists(),
        }
        for team_id, t in meta.items()
    ]


def _has_face_swap_model() -> bool:
    """Verifica si el modelo de face swap está disponible."""
    return (config.MODELS_DIR / "inswapper_128.onnx").exists()


def generate_card(team_id: str, user_photo_bytes: bytes, data: dict) -> bytes:
    meta = load_templates_meta()
    if team_id not in meta:
        raise KeyError(f"Equipo desconocido: {team_id}")

    template_path = config.TEMPLATES_DIR / meta[team_id]["file"]
    if not template_path.exists():
        raise FileNotFoundError(
            f"Plantilla no encontrada: {template_path.name}. "
            "Coloca tu plantilla limpia en assets/templates/ (ver README)."
        )

    # 1. Cargar plantilla (ya limpia de textos, ver scripts/clean_template.py)
    template_bgr = cv2.imread(str(template_path), cv2.IMREAD_COLOR)

    # 2. Decodificar la foto del usuario
    arr = np.frombuffer(user_photo_bytes, dtype=np.uint8)
    user_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if user_bgr is None:
        raise ValueError("La foto subida no es una imagen válida (usa JPG o PNG).")

    # 3. Reemplazo de rostro/cabeza según el modo configurado
    swap_mode = os.getenv("SWAP_MODE", "face")
    if swap_mode == "head":
        # Cabeza completa (pelo + cuello) por composición con segmentación
        from . import head_swap

        swapped_bgr = head_swap.swap_head(template_bgr, user_bgr)
        # Refinar el rostro interior con inswapper si el modelo está disponible
        if _has_face_swap_model():
            try:
                swapped_bgr = face_swap.swap_face(swapped_bgr, user_bgr)
            except Exception:
                pass  # la composición ya lleva el rostro del usuario
    elif _has_face_swap_model():
        swapped_bgr = face_swap.swap_face(template_bgr, user_bgr)
    else:
        swapped_bgr = template_bgr

    # 4. Renderizar textos con Pillow (RGB)
    img = Image.fromarray(cv2.cvtColor(swapped_bgr, cv2.COLOR_BGR2RGB))
    img = text_renderer.render_card_text(img, data, meta[team_id]["layout"])

    # 5. PNG final
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
