# Build from the repository root:  docker build -f playground/Dockerfile -t sentinel-playground .
# WITH_CLASSIFIERS=0 builds a small image (rules only) for quick tests; the published image uses 1.
FROM python:3.12-slim
ARG WITH_CLASSIFIERS=1
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HOME=/models
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic pyyaml
RUN pip install --no-cache-dir "ai-sentinel @ git+https://github.com/yurtseveronder-design/ai-sentinel.git@main"
RUN if [ "$WITH_CLASSIFIERS" = "1" ]; then \
      pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch && \
      pip install --no-cache-dir "sentinel-semantic[classifier] @ git+https://github.com/yurtseveronder-design/sentinel-semantic.git@main"; \
    else \
      pip install --no-cache-dir "sentinel-semantic @ git+https://github.com/yurtseveronder-design/sentinel-semantic.git@main"; \
    fi
# Download both classifier models at build time so the server starts offline and quickly.
RUN if [ "$WITH_CLASSIFIERS" = "1" ]; then \
      python -c "from transformers import pipeline; [pipeline('text-classification', model=m) for m in ('protectai/deberta-v3-base-prompt-injection-v2','deepset/deberta-v3-base-injection')]"; \
    fi

COPY rag_demo rag_demo
COPY playground playground
COPY docs docs
RUN useradd -m -u 1000 user && chmod -R a+rX /models /app 2>/dev/null || true
USER 1000
ENV PORT=7860 WITH_CLASSIFIERS=${WITH_CLASSIFIERS}
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:7860/health')"
CMD ["sh", "-c", "if [ \"$WITH_CLASSIFIERS\" = \"0\" ]; then export PLAYGROUND_MODES=rules; fi; exec uvicorn playground.app:app --host 0.0.0.0 --port ${PORT}"]
