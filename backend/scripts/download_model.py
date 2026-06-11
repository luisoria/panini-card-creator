"""Descarga el modelo de face swap al arrancar el contenedor, si no existe.

Controlado por variables de entorno:
- INSWAPPER_MODEL_PATH: destino del .onnx (default: assets/models/inswapper_128.onnx)
- MODEL_URL: URL de descarga. Si está vacía o el archivo ya existe, no hace nada
  (el backend funciona igual, solo que sin face swap).
"""
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config


def main():
    dest = Path(config.INSWAPPER_MODEL_PATH)
    url = os.getenv("MODEL_URL", "").strip()

    if dest.exists() and dest.stat().st_size > 100_000_000:
        print(f"[model] ya existe: {dest} ({dest.stat().st_size // 1_000_000} MB)")
        return
    if not url:
        print("[model] MODEL_URL no definida; el backend arrancará sin face swap.")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    print(f"[model] descargando {url} -> {dest} (~530 MB, puede tardar varios minutos)")

    def progress(blocks, block_size, total):
        done = blocks * block_size
        if total > 0 and blocks % 2000 == 0:
            print(f"[model] {done // 1_000_000} / {total // 1_000_000} MB", flush=True)

    try:
        urllib.request.urlretrieve(url, tmp, reporthook=progress)
        tmp.rename(dest)
        print(f"[model] descarga completa: {dest.stat().st_size // 1_000_000} MB")
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print(f"[model] ERROR descargando el modelo: {e}. Arrancando sin face swap.")


if __name__ == "__main__":
    main()
