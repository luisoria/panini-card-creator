"""Head swap por composición: cabeza completa (pelo + rostro + cuello) del
usuario sobre la tarjeta, fundiendo el cuello con la camiseta del jugador.

Pipeline:
 1. Detectar rostro en ambas imágenes (InsightFace si está disponible, si no
    Haar de OpenCV) para obtener escala y punto de anclaje.
 2. Segmentar a la persona en la foto del usuario (rembg/u2net) y recortar la
    cabeza con cuello, desvaneciendo el alfa hacia abajo.
 3. Borrar la cabeza original de la plantilla (segmentación + inpainting).
 4. Pegar la cabeza del usuario escalada y alineada por el rostro.
 5. Restaurar la camiseta/cuello de la plantilla por encima, para que la
    cabeza nueva quede "metida" dentro de la franela.
"""
import io
import logging
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Proporciones relativas al alto del rostro detectado (ajustables)
HAIR_MARGIN = 1.10      # espacio sobre el rostro para incluir el pelo
SIDE_MARGIN = 0.75      # espacio lateral (orejas / pelo)
NECK_LENGTH = 0.55      # cuánto cuello conservar bajo la barbilla
NECK_FADE = 0.25        # tramo final del cuello con desvanecido alfa
COLLAR_LINE = 0.32      # dónde empieza la camiseta bajo la barbilla (plantilla)


@lru_cache(maxsize=1)
def _rembg_session():
    from rembg import new_session

    return new_session("u2net_human_seg")


def _person_alpha(img_bgr: np.ndarray) -> np.ndarray:
    """Máscara alfa (0-255) de la persona en la imagen."""
    from rembg import remove

    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    out = remove(Image.fromarray(rgb), session=_rembg_session())
    return np.array(out)[:, :, 3]


def _face_box(img_bgr: np.ndarray) -> dict:
    """Rostro principal: bbox + anclaje. InsightFace en servidor, Haar local."""
    try:
        from .face_swap import _get_models  # reutiliza el analizador cargado

        analyzer, _ = _get_models()
        faces = analyzer.get(img_bgr)
        if faces:
            f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            x1, y1, x2, y2 = f.bbox
            kps = f.kps  # ojos, nariz, comisuras
            anchor = ((kps[0][0] + kps[1][0]) / 2, (kps[0][1] + kps[1][1]) / 2)
            return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "w": x2 - x1,
                    "h": y2 - y1, "anchor": anchor}
    except Exception:
        logger.info("InsightFace no disponible para detección; usando Haar.")

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    if len(faces) == 0:
        raise ValueError("No se detectó un rostro en la imagen.")
    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
    # Haar: bbox algo más amplio que el rostro; el anclaje ~ línea de ojos
    return {"x1": x, "y1": y, "x2": x + w, "y2": y + h, "w": w, "h": h,
            "anchor": (x + w / 2, y + h * 0.42)}


def _cut_user_head(user_bgr: np.ndarray, uf: dict) -> tuple:
    """Recorta cabeza+cuello del usuario con alfa desvanecido en el cuello.

    Devuelve (bgr, alpha, anchor_en_recorte).
    """
    H, W = user_bgr.shape[:2]
    alpha = _person_alpha(user_bgr)

    x1 = int(max(0, uf["x1"] - SIDE_MARGIN * uf["w"]))
    x2 = int(min(W, uf["x2"] + SIDE_MARGIN * uf["w"]))
    y1 = int(max(0, uf["y1"] - HAIR_MARGIN * uf["h"]))
    neck_end = int(min(H, uf["y2"] + NECK_LENGTH * uf["h"]))

    crop = user_bgr[y1:neck_end, x1:x2].copy()
    a = alpha[y1:neck_end, x1:x2].astype(np.float32)

    # Desvanecer el tramo final del cuello para fundir con la camiseta
    fade_px = max(2, int(NECK_FADE * uf["h"]))
    ramp = np.linspace(1.0, 0.0, fade_px)[:, None]
    a[-fade_px:] *= ramp

    # Suavizar bordes de la segmentación
    a = cv2.GaussianBlur(a, (7, 7), 0)
    anchor = (uf["anchor"][0] - x1, uf["anchor"][1] - y1)
    return crop, a, anchor


def _remove_template_head(template_bgr: np.ndarray, tf: dict) -> np.ndarray:
    """Borra la cabeza del jugador reconstruyendo el fondo con inpainting."""
    H, W = template_bgr.shape[:2]
    alpha = _person_alpha(template_bgr)

    neck_y = int(min(H, tf["y2"] + NECK_LENGTH * tf["h"]))
    head_mask = np.zeros((H, W), np.uint8)
    head_mask[:neck_y] = (alpha[:neck_y] > 100).astype(np.uint8) * 255
    head_mask = cv2.dilate(
        head_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    )
    return cv2.inpaint(template_bgr, head_mask, 7, cv2.INPAINT_TELEA), alpha


def swap_head(template_bgr: np.ndarray, user_bgr: np.ndarray) -> np.ndarray:
    tf = _face_box(template_bgr)
    uf = _face_box(user_bgr)

    head, head_a, anchor = _cut_user_head(user_bgr, uf)
    clean_bg, t_alpha = _remove_template_head(template_bgr, tf)

    # Escalar para que el rostro del usuario mida lo mismo que el del jugador
    scale = tf["w"] / uf["w"]
    nh, nw = int(head.shape[0] * scale), int(head.shape[1] * scale)
    head = cv2.resize(head, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    head_a = cv2.resize(head_a, (nw, nh), interpolation=cv2.INTER_LINEAR)
    ax, ay = anchor[0] * scale, anchor[1] * scale

    # Posicionar: anclaje (línea de ojos) del usuario sobre el del jugador
    H, W = template_bgr.shape[:2]
    ox, oy = int(tf["anchor"][0] - ax), int(tf["anchor"][1] - ay)

    out = clean_bg.astype(np.float32)
    sx1, sy1 = max(0, -ox), max(0, -oy)
    dx1, dy1 = max(0, ox), max(0, oy)
    dx2, dy2 = min(W, ox + nw), min(H, oy + nh)
    if dx2 <= dx1 or dy2 <= dy1:
        raise ValueError("La cabeza quedó fuera de la tarjeta; usa una foto más centrada.")

    region_a = (head_a[sy1:sy1 + dy2 - dy1, sx1:sx1 + dx2 - dx1] / 255.0)[..., None]
    region = head[sy1:sy1 + dy2 - dy1, sx1:sx1 + dx2 - dx1].astype(np.float32)
    out[dy1:dy2, dx1:dx2] = region * region_a + out[dy1:dy2, dx1:dx2] * (1 - region_a)

    # Restaurar la camiseta encima para "meter" el cuello nuevo en la franela
    collar_y = int(tf["y2"] + COLLAR_LINE * tf["h"])
    body_mask = np.zeros((H, W), np.float32)
    body_mask[collar_y:] = (t_alpha[collar_y:] > 100).astype(np.float32)
    body_mask = cv2.GaussianBlur(body_mask, (11, 11), 0)[..., None]
    out = template_bgr.astype(np.float32) * body_mask + out * (1 - body_mask)

    return np.clip(out, 0, 255).astype(np.uint8)
