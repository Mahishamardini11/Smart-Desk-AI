# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# Install minimal system deps needed by chromadb/tokenizers (no build-essential needed for slim wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ── Layer 1: CPU-only PyTorch (heaviest package, rarely changes) ──────────────
# BuildKit cache mount keeps the pip cache between builds — no re-download.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

# ── Layer 2: Application dependencies ─────────────────────────────────────────
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ── Layer 3: Pre-bake models (cached unless layers 1-2 change) ────────────────
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2'); \
from transformers import pipeline; \
pipeline('text2text-generation', model='MBZUAI/LaMini-Flan-T5-77M')\
"

# ── Layer 4: Application source (changes most often — last layer) ─────────────
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
