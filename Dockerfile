FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY docs/api-coverage-matrix.md /tmp/api-coverage-matrix.md

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && mkdir -p /usr/local/lib/python3.12/docs \
    && cp /tmp/api-coverage-matrix.md /usr/local/lib/python3.12/docs/api-coverage-matrix.md \
    && rm /tmp/api-coverage-matrix.md

RUN useradd --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

USER appuser

EXPOSE 8000

ENTRYPOINT ["followupboss-mcp-hosted"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--path", "/mcp"]
