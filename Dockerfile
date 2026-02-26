# -----------------------------
# 1) Frontend build stage
# -----------------------------
FROM node:20-slim AS frontend-build
WORKDIR /frontend

# Install deps first (better caching)
COPY package*.json ./
RUN npm ci

# Copy the rest of the frontend source
COPY . .

# Your build script runs pyodide fetch and writes into static/pyodide
# (your zip didn’t include static/, so ensure it exists)
RUN mkdir -p static/pyodide

ENV NODE_OPTIONS=--max-old-space-size=4096
# Build (Vite/SvelteKit/etc.)
ARG BUILD_HASH=local
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN npm run build

# -----------------------------
# 2) Runtime stage (Python + Ollama + built frontend)
# -----------------------------
FROM python:3.11-slim AS runtime
WORKDIR /app

# System deps (curl for installing Ollama, tini for clean signal handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates bash tini zstd xz-utils git \
  && rm -rf /var/lib/apt/lists/*


# Install Ollama (CPU)
# (Models will be downloaded at runtime into the mounted volume)
RUN curl -fsSL https://ollama.com/install.sh | bash

# ---- Python deps ----
# If you have backend/requirements.txt, use it. If you use pyproject, adapt accordingly.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code
COPY backend /app/backend
COPY CHANGELOG.md /app/CHANGELOG.md
COPY CHANGELOG.md /app/backend/open_webui/CHANGELOG.md


# Copy built frontend output into /app/build
# Adjust this if your build output directory differs.
# Common outputs: "build" (SvelteKit adapter-node/static build), or "dist" (Vite).
# If your output is "dist", change /frontend/build -> /frontend/dist.
COPY --from=frontend-build /frontend/build /app/build

# Runtime defaults
ENV PORT=8080
ENV UVICORN_APP="open_webui.main:app"
ENV UVICORN_APP_DIR="/app/backend"
ENV UVICORN_HOST="0.0.0.0"

# Ollama persistence location (make this point into your mounted Fly volume)
ENV OLLAMA_MODELS="/app/backend/data/ollama"
# Keep Ollama bound locally inside container
ENV OLLAMA_HOST="127.0.0.1:11434"
ENV OLLAMA_BASE_URL="http://127.0.0.1:11434"

# RAG embeddings via Ollama
ENV RAG_EMBEDDING_ENGINE="ollama"
ENV RAG_EMBEDDING_MODEL="mxbai-embed-large"

# Ensure data dirs exist
RUN mkdir -p /app/backend/data /app/backend/data/ollama

# Initialize minimal git repo so GitPython doesn't crash
RUN git init /app && \
    git config --global user.email "docker@example.com" && \
    git config --global user.name "Docker" && \
    cd /app && \
    touch .gitkeep && \
    git add .gitkeep && \
    git commit -m "init"

# Entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

# Use tini as PID 1, then run entrypoint
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
CMD ["/app/entrypoint.sh"]
