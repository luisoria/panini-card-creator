"""Head swap generativo con Gemini (imagen) — "Nano Banana".

Envía la plantilla limpia + la foto del usuario y pide reemplazar la cabeza
del jugador manteniendo el resto de la tarjeta intacto. Al ser un modelo
generativo, re-dibuja la transición cuello/camiseta de forma fotorrealista.

Requiere GEMINI_API_KEY (gratis en https://aistudio.google.com/apikey).
"""
import base64
import logging
import os

import cv2
import numpy as np
import requests

from .. import config

logger = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = (
    "Replace the head of the soccer player in the first image with the head of "
    "the person in the second image, including their hairstyle and skin tone. "
    "Keep everything else in the first image exactly unchanged: same jersey and "
    "collar, same background graphics and colors, same framing, same proportions "
    "and same image size. Blend the new head photorealistically: match the studio "
    "lighting of the card and make a natural neck transition into the jersey "
    "collar. Return only the edited first image."
)


def _to_inline(img_bgr: np.ndarray) -> dict:
    ok, buf = cv2.imencode(".png", img_bgr)
    return {
        "inline_data": {
            "mime_type": "image/png",
            "data": base64.b64encode(buf.tobytes()).decode(),
        }
    }


def swap(template_bgr: np.ndarray, user_bgr: np.ndarray) -> np.ndarray:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("FACESWAP_PROVIDER=gemini pero falta GEMINI_API_KEY")

    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    body = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                _to_inline(template_bgr),
                _to_inline(user_bgr),
            ]
        }],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }

    resp = requests.post(
        API_URL.format(model=model),
        json=body,
        headers={"x-goog-api-key": api_key},
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")

    parts = resp.json()["candidates"][0]["content"]["parts"]
    img_b64 = next(
        (p["inlineData"]["data"] for p in parts if "inlineData" in p),
        None,
    ) or next(
        (p["inline_data"]["data"] for p in parts if "inline_data" in p),
        None,
    )
    if not img_b64:
        raise RuntimeError("Gemini no devolvió imagen (posible bloqueo de contenido).")

    arr = np.frombuffer(base64.b64decode(img_b64), dtype=np.uint8)
    out = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if out is None:
        raise RuntimeError("No se pudo decodificar la imagen devuelta por Gemini.")

    # Gemini puede devolver otra resolución: volver al tamaño de la plantilla
    h, w = template_bgr.shape[:2]
    if out.shape[:2] != (h, w):
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LANCZOS4)
    return out
