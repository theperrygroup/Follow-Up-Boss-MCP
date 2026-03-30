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

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN useradd --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

USER appuser

EXPOSE 8000

ENTRYPOINT ["followupboss-mcp-hosted"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--path", "/mcp"]
