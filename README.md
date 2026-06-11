# Card Creator — Tarjetas Personalizadas Estilo Álbum Mundial 2026

Sistema web que genera tarjetas de jugador personalizadas: recibe la foto del rostro
del usuario + datos en texto, hace **face swap** sobre la plantilla del equipo elegido
(sin alterar uniforme, fondo ni estructura) y renderiza los datos con la tipografía
correcta.

> **⚠️ Aviso legal:** este proyecto es *agnóstico a la plantilla*. Las imágenes base
> (tarjetas) **no se incluyen** y debes aportarlas tú en `backend/assets/templates/`.
> Los diseños, el logo de Panini y el logo oficial del Mundial son marcas registradas:
> úsalo solo con plantillas propias/licenciadas o para uso estrictamente personal.

## Arquitectura

```
┌─────────────┐  multipart/form-data   ┌──────────────────────────┐
│  Next.js    │ ─────────────────────► │  FastAPI (Python)        │
│  (frontend) │   foto + datos + team  │  1. carga plantilla limpia│
│  :3000      │ ◄───────────────────── │  2. face swap (InsightFace)│
└─────────────┘     PNG final          │  3. texto (Pillow)        │
                                       └──────────────────────────┘
```

## Estructura del proyecto

```
.
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                 # Endpoints FastAPI
│   │   ├── config.py               # Rutas y settings
│   │   ├── templates.json          # Metadatos/layout por equipo
│   │   └── services/
│   │       ├── face_swap.py        # InsightFace + inswapper_128
│   │       ├── text_renderer.py    # Pillow: tipografía y centrado
│   │       └── pipeline.py         # Orquestación del proceso
│   ├── scripts/
│   │   └── clean_template.py       # Inpainting one-shot (borrar texto original)
│   └── assets/
│       ├── templates/              # ← TUS plantillas (colombia.png, brasil.png…)
│       ├── fonts/                  # ← BebasNeue-Regular.ttf, RobotoCondensed-*.ttf
│       └── models/                 # ← inswapper_128.onnx
└── frontend/
    ├── Dockerfile
    ├── app/                        # Next.js App Router
    ├── components/                 # TeamSelector, PhotoUploader, PlayerForm, CardPreview
    └── lib/api.ts
```

## Estado de los assets

| Asset | Estado | Destino |
|---|---|---|
| Plantillas limpias (5 equipos) | ✅ generadas con `scripts/prepare_templates.py` desde `Template of image/` | `backend/assets/templates/*.png` |
| Bebas Neue (OFL) | ✅ descargada de Google Fonts | `backend/assets/fonts/BebasNeue-Regular.ttf` |
| Roboto Condensed variable (OFL) | ✅ descargada de Google Fonts | `backend/assets/fonts/RobotoCondensed-Variable.ttf` |
| Modelo `inswapper_128.onnx` | ⬜ **pendiente** — buscar "inswapper_128" en Hugging Face (~530 MB) | `backend/assets/models/inswapper_128.onnx` |

> *DIN Condensed Bold* es una fuente comercial; Bebas Neue es la alternativa libre
> visualmente equivalente. Si tienes licencia de DIN, colócala en `fonts/` y ajusta
> `config.py`. Si no quieres descargar el modelo, usa `FACESWAP_PROVIDER=replicate`.

## Setup

### 1. Preparar / re-preparar plantillas

`scripts/prepare_templates.py` convierte las imágenes de `Template of image/` a PNG
y borra los textos originales rellenando con el color plano de cada píldora:

```bash
cd backend
python scripts/prepare_templates.py
```

Para plantillas nuevas con fondos complejos detrás del texto existe la variante
manual con inpainting por máscara:

```bash
python scripts/clean_template.py plantilla.png mascara.png salida.png
```

### 2. Registrar equipos nuevos en `backend/app/templates.json`

Las coordenadas son **fracciones relativas** (0.0–1.0) del alto/ancho de la imagen,
así funcionan a cualquier resolución. Calibra con:

```bash
python scripts/test_render.py colombia   # genera assets/templates/_test_render.png
```

### 3. Levantar con Docker

```bash
docker compose up --build
# Frontend → http://localhost:3000
# Backend  → http://localhost:8000/docs
```

### Desarrollo sin Docker

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Alternativa: Face Swap vía Replicate

Si no quieres correr InsightFace localmente (CPU lenta / sin el .onnx), define
`FACESWAP_PROVIDER=replicate` y `REPLICATE_API_TOKEN` en el entorno del backend.
Ver `face_swap.py` para el punto de extensión.
