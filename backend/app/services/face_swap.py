"""Face swap: reemplaza el rostro de la plantilla por el del usuario.

inswapper_128 solo modifica la región facial (con blending de bordes), por lo
que cuello, camiseta, fondo y gráfica de la tarjeta quedan intactos.
"""
import logging
from functools import lru_cache

import cv2
import numpy as np

from .. import config

logger = logging.getLogger(__name__)


def _has_insightface() -> bool:
    """Verifica si insightface está instalado y el modelo está disponible."""
    try:
        import os
        if not (config.MODELS_DIR / "inswapper_128.onnx").exists():
            return False
        from insightface.app import FaceAnalysis  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _get_models():
    """Carga perezosa y única de los modelos de InsightFace."""
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model

    analyzer = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    analyzer.prepare(ctx_id=0, det_size=(640, 640))

    swapper = get_model(config.INSWAPPER_MODEL_PATH, providers=["CPUExecutionProvider"])
    return analyzer, swapper


def _largest_face(faces):
    return max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
    )


def swap_face(template_bgr: np.ndarray, user_photo_bgr: np.ndarray) -> np.ndarray:
    """Devuelve la plantilla con el rostro del usuario aplicado sobre el del jugador.
    
    Si no hay modelo de face swap disponible, devuelve la plantilla original sin modificar.
    """
    if config.FACESWAP_PROVIDER == "replicate":
        return _swap_via_replicate(template_bgr, user_photo_bgr)

    if not _has_insightface():
        logger.warning(
            "Modelo de face swap no disponible. "
            "Usando plantilla original sin modificar. "
            "Descarga inswapper_128.onnx a backend/assets/models/"
        )
        return template_bgr

    analyzer, swapper = _get_models()

    src_faces = analyzer.get(user_photo_bgr)
    if not src_faces:
        raise ValueError(
            "No se detectó un rostro en la foto subida. "
            "Usa una foto frontal, bien iluminada y sin obstrucciones."
        )
    dst_faces = analyzer.get(template_bgr)
    if not dst_faces:
        raise ValueError("No se detectó el rostro del jugador en la plantilla base.")

    source = _largest_face(src_faces)
    target = _largest_face(dst_faces)

    # paste_back=True: inswapper recompone solo el área facial sobre la imagen
    # original, preservando uniforme, fondo y estructura de la tarjeta.
    result = swapper.get(template_bgr, target, source, paste_back=True)
    return result


def _swap_via_replicate(template_bgr: np.ndarray, user_photo_bgr: np.ndarray) -> np.ndarray:
    """Face swap via Replicate API.
    
    Uses the popular face-swap model. Requires REPLICATE_API_TOKEN.
    """
    import base64
    import time

    import requests

    if not config.REPLICATE_API_TOKEN:
        raise RuntimeError("FACESWAP_PROVIDER=replicate pero falta REPLICATE_API_TOKEN")

    def to_base64(img_bgr):
        ok, buf = cv2.imencode(".png", img_bgr)
        return base64.b64encode(buf).decode()

    headers = {
        "Authorization": f"Bearer {config.REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": "8d492cd1c2839c499f8b209e0d5b3df9e04db6b9c73a2d541d48dd3a1c67c9c9",
        "input": {
            "source_image": to_base64(user_photo_bgr),
            "target_image": to_base64(template_bgr),
        },
    }
    resp = requests.post(
        "https://api.replicate.com/v1/predictions", json=payload, headers=headers, timeout=60
    )
    resp.raise_for_status()
    prediction = resp.json()

    while prediction["status"] in ("in_progress", "starting"):
        time.sleep(2)
        prediction = requests.get(
            prediction["urls"]["get"], headers=headers, timeout=30
        ).json()

    if prediction["status"] != "succeeded":
        raise RuntimeError(f"Replicate falló: {prediction.get('error', 'unknown error')}")

    out_url = prediction["output"]
    if isinstance(out_url, list):
        out_url = out_url[0]
    img_bytes = requests.get(out_url, timeout=60).content
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)
