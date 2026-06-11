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
NECK_LENGTH = 0.42      # cuánto cuello conservar bajo la barbilla
NECK_FADE = 0.30        # tramo final del cuello con desvanecido alfa
NECK_HALF_W = 0.32      # semiancho de la columna de cuello (x ancho de rostro)
COLLAR_LINE = 0.30      # dónde empieza la camiseta bajo la barbilla (plantilla)
SKIN_DELTA = 26.0       # distancia Lab máx. para considerar un píxel "piel"


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

    # Bajo la barbilla, conservar SOLO la columna del cuello: fuera quedan
    # hombros y ropa de la foto origen (causa clásica de "montaje" visible)
    chin_row = int(max(0, uf["y2"] - y1))
    if chin_row < a.shape[0]:
        cx = (uf["x1"] + uf["x2"]) / 2 - x1
        xs = np.arange(a.shape[1], dtype=np.float32)
        soft = 0.18 * uf["w"]
        band = np.clip((NECK_HALF_W * uf["w"] + soft - np.abs(xs - cx)) / soft, 0, 1)
        a[chin_row:] *= band[None, :]

    # Desvanecer el tramo final del cuello para fundir con la camiseta
    fade_px = max(2, int(NECK_FADE * uf["h"]))
    ramp = np.linspace(1.0, 0.0, fade_px)[:, None]
    a[-fade_px:] *= ramp

    # Suavizar bordes de la segmentación
    a = cv2.GaussianBlur(a, (7, 7), 0)
    anchor = (uf["anchor"][0] - x1, uf["anchor"][1] - y1)
    return crop, a, anchor


def _skin_lab(img_bgr: np.ndarray, box: dict) -> np.ndarray:
    """Color medio de piel (Lab) en el interior del rostro detectado."""
    x1, y1 = int(box["x1"] + 0.25 * box["w"]), int(box["y1"] + 0.35 * box["h"])
    x2, y2 = int(box["x2"] - 0.25 * box["w"]), int(box["y2"] - 0.15 * box["h"])
    patch = img_bgr[max(0, y1):y2, max(0, x1):x2]
    lab = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    return np.median(lab, axis=0)


def _match_head_luminance(head: np.ndarray, u_skin: np.ndarray,
                          t_skin: np.ndarray, weight: float = 0.65) -> np.ndarray:
    """Acerca la luminancia de la cabeza a la de la tarjeta sin alterar el tono."""
    lab = cv2.cvtColor(head, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:, :, 0] += weight * (t_skin[0] - u_skin[0])
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def _recolor_template_skin(template_bgr: np.ndarray, t_skin: np.ndarray,
                           u_skin: np.ndarray) -> np.ndarray:
    """Desplaza la piel expuesta de la plantilla (pecho/cuello del jugador en
    la "V" de la camiseta) hacia el tono de piel del usuario."""
    lab = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    dist = np.linalg.norm(lab - t_skin[None, None, :], axis=2)
    w = np.clip(1.0 - dist / SKIN_DELTA, 0, 1)
    w = cv2.GaussianBlur(w, (9, 9), 0)[..., None]
    shifted = lab + (u_skin - t_skin)[None, None, :]
    lab = shifted * w + lab * (1 - w)
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


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

    # Integración de color: luz de la tarjeta sobre la cabeza, y piel del
    # jugador (pecho en la "V") hacia el tono del usuario
    u_skin, t_skin = _skin_lab(user_bgr, uf), _skin_lab(template_bgr, tf)
    head = _match_head_luminance(head, u_skin, t_skin)
    body_source = _recolor_template_skin(template_bgr, t_skin, u_skin)

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
    # (usando la versión con la piel del jugador re-coloreada al tono del usuario)
    collar_y = int(tf["y2"] + COLLAR_LINE * tf["h"])
    body_mask = np.zeros((H, W), np.float32)
    body_mask[collar_y:] = (t_alpha[collar_y:] > 100).astype(np.float32)
    body_mask = cv2.GaussianBlur(body_mask, (11, 11), 0)[..., None]
    out = body_source.astype(np.float32) * body_mask + out * (1 - body_mask)

    return np.clip(out, 0, 255).astype(np.uint8)
