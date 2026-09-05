# Canonical MandateGuard judge application.
# Serves the same FastAPI + public/ workspace used in the submission demo.
# No provider credentials are required and the runtime is forced offline.
#
#   docker build -t mandateguard .
#   docker run --rm -p 8765:8765 mandateguard

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MANDATEGUARD_OFFLINE=1
ENV PORT=8765

# Install runtime dependencies before copying evidence/static assets so
# presentation-only edits retain the dependency layer cache.
COPY pyproject.toml README.md ./
COPY bailiff ./bailiff
RUN pip install --no-cache-dir -e .

COPY api ./api
COPY public ./public
COPY outputs ./outputs
COPY docs/testmode_evidence ./docs/testmode_evidence

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8765\")}/api/health', timeout=3)" || exit 1

CMD ["sh", "-c", "python -m uvicorn api.index:app --host 0.0.0.0 --port ${PORT}"]
