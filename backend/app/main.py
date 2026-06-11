"""API del generador de tarjetas personalizadas."""
import logging
import os
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import config
from .services import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("card-api")

app = FastAPI(title="Card Creator API", version="1.0.0")

# Orígenes permitidos configurables: CORS_ORIGINS=https://mi-dominio,https://otro
_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATE_RE = re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/teams")
def teams():
    """Equipos disponibles (available=False si falta la plantilla en assets)."""
    return pipeline.list_teams()


@app.post("/api/generate-card")
async def generate_card(
    team: str = Form(..., description="ID del equipo, ej. 'colombia'"),
    player_name: str = Form(..., min_length=2, max_length=40),
    birth_date: str = Form(..., description="DD-MM-YYYY"),
    height: str = Form(..., description="ej. 1,80 m"),
    weight: str = Form(..., description="ej. 70 kg"),
    club: str = Form(..., min_length=2, max_length=60, description="ej. FC BAYERN MÜNCHEN (GER)"),
    photo: UploadFile = File(..., description="Foto frontal del rostro"),
):
    if not DATE_RE.match(birth_date.strip()):
        raise HTTPException(422, "Fecha inválida: usa el formato DD-MM-YYYY (ej. 13-1-1997).")

    photo_bytes = await photo.read()
    if len(photo_bytes) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"La foto supera {config.MAX_UPLOAD_MB} MB.")

    data = {
        "name": player_name,
        "birth_date": birth_date.strip(),
        "height": height.strip(),
        "weight": weight.strip(),
        "club": club,
    }

    try:
        png = pipeline.generate_card(team, photo_bytes, data)
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception:
        logger.exception("Error generando la tarjeta")
        raise HTTPException(
            500,
            "Error interno procesando la imagen. "
            "Verifica que el modelo inswapper_128.onnx está en backend/assets/models/",
        )

    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="card.png"'},
    )
