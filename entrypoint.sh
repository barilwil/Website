#!/usr/bin/env bash
set -euo pipefail

# Start Ollama in the background
ollama serve &
OLLAMA_PID=$!

# Start backend
exec uvicorn "${UVICORN_APP}" --app-dir "${UVICORN_APP_DIR}" \
  --host "${UVICORN_HOST}" --port "${PORT}"