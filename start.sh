#!/bin/bash

# Inicia la API (FastAPI) en segundo plano
uvicorn src.api.api:app --host 0.0.0.0 --port 8000 &

# Inicia la aplicación Gradio (este comando se bloquea)
python -m src.gradio.app --server-name="0.0.0.0" --server-port=7860 