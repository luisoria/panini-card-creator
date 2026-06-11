import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
FONTS_DIR = ASSETS_DIR / "fonts"
MODELS_DIR = ASSETS_DIR / "models"

TEMPLATES_META = Path(__file__).resolve().parent / "templates.json"

# Proveedor de face swap: "insightface" (local) | "replicate" (API)
FACESWAP_PROVIDER = os.getenv("FACESWAP_PROVIDER", "insightface")
INSWAPPER_MODEL_PATH = os.getenv(
    "INSWAPPER_MODEL_PATH", str(MODELS_DIR / "inswapper_128.onnx")
)
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

FONT_NAME = "BebasNeue-Regular.ttf"          # alternativa libre a DIN Condensed Bold
# Roboto Condensed variable: el peso se selecciona por variación en el renderer
FONT_STATS = "RobotoCondensed-Variable.ttf"
FONT_STATS_BOLD = "RobotoCondensed-Variable.ttf"

MAX_UPLOAD_MB = 10
