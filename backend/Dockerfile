FROM python:3.11-slim

# Dependencias nativas de OpenCV / onnxruntime + toolchain para compilar insightface
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
# assets/ (plantillas, fuentes, modelo onnx) se monta como volumen — ver docker-compose.yml

EXPOSE 8000
# Descarga el modelo de face swap si falta (MODEL_URL) y arranca la API
CMD ["sh", "-c", "python scripts/download_model.py; exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
