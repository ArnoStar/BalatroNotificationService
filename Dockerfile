# syntax=docker/dockerfile:1
# The notification service in a container: it consumes RabbitMQ (RABBITMQ_URL)
# and sends the emails; http://<host>:8000/health says whether it consumes.
#
#   docker build --network host -t balatro-notification .
#   docker run --env-file .env balatro-notification

FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim
RUN useradd --system --uid 10001 --no-create-home notification
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY app ./app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1
USER notification
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
