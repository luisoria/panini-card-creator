"""Diagnóstico de cuota/modelos de imagen de Gemini para la API key dada."""
import json
import os

import requests

KEY = os.environ["GEMINI_API_KEY"]
BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def call(model, body):
    r = requests.post(
        f"{BASE}/{model}:generateContent",
        json=body,
        headers={"x-goog-api-key": KEY},
        timeout=60,
    )
    return r


# 1. ¿La key funciona con un modelo de texto?
r = call("gemini-2.5-flash", {"contents": [{"parts": [{"text": "di hola"}]}]})
print("texto gemini-2.5-flash ->", r.status_code)

# 2. Modelos de imagen: estado y detalle de cuota
for model in ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]:
    r = call(model, {
        "contents": [{"parts": [{"text": "a plain red circle on white"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    })
    print(f"imagen {model} ->", r.status_code)
    if r.status_code != 200:
        try:
            err = r.json().get("error", {})
            print("  msg:", err.get("message", "")[:160])
            for d in err.get("details", []):
                for v in d.get("violations", []):
                    print("  VIOLACION:", json.dumps(v)[:300])
                if "retryDelay" in d:
                    print("  retryDelay:", d["retryDelay"])
        except Exception:
            print("  body:", r.text[:200])
