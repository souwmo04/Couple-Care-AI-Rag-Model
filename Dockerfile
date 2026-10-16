# CoupleCare AI — single-container deployment (Hugging Face Spaces, Docker SDK).
# Replies come from Groq (cloud mode); there is no GPU or local model in the container.
# Set the Space secret COUPLECARE_GROQ_API_KEY. See docs/deploy-huggingface.md.

# ---------------------------------------------------------------- 1. build the website
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------- 2. backend + built website
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Hugging Face runs containers as user 1000.
RUN useradd --create-home --uid 1000 user
WORKDIR /app

COPY requirements.txt ./
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

COPY --chown=user backend/ backend/
COPY --chown=user data/ data/
COPY --chown=user scripts/build_index.py scripts/build_index.py
COPY --chown=user --from=web /web/dist frontend/dist
RUN mkdir -p artifacts/indexes data/user .cache && chown -R user:user /app
USER user

ENV HF_HOME=/app/.cache/huggingface \
    COUPLECARE_LLM_PROVIDER=groq \
    COUPLECARE_GROQ_FALLBACK_LOCAL=false \
    COUPLECARE_FRONTEND_DIST=/app/frontend/dist \
    COUPLECARE_FRAME_ANCESTORS=https://huggingface.co

# Build the knowledge index now (downloads the multilingual-e5-small embedding model once), so the app
# starts quickly and does not download anything at runtime.
RUN python scripts/build_index.py

EXPOSE 7860
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
