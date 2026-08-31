FROM ghcr.io/astral-sh/uv:0.11.32@sha256:df4cae8f3a96d175e2e5f992e597550000edbe78fdc2594d5cd8de1a217f504c AS uv
FROM python:3.12-slim@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src
COPY docs/api-coverage-matrix.md /app/docs/api-coverage-matrix.md

RUN uv sync --frozen --no-dev --no-editable

RUN useradd --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser

USER appuser

EXPOSE 8000

ENTRYPOINT ["followupboss-mcp-hosted"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--path", "/mcp"]
