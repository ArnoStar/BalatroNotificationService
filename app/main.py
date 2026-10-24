"""``uvicorn app.main:app``: the queue consumer, and an HTTP API for its
health. Settings come from the environment (or .env): see .env.example."""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap.container import Container
from app.infrastructure.config.settings import Settings, get_settings
from app.presentation.api.routes.meta import router as meta_router

DESCRIPTION = """
Sends Balatro's emails. The other services publish messages to RabbitMQ
(exchange `notifications`); this service renders and sends them. For now: the
identity service's confirmation codes (`email.confirmation_code`). See
docs/messages.md.
"""


def create_app(
    settings: Settings | None = None,
    container_factory: Callable[[Settings], Container] = Container,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = container_factory(settings)
        app.state.container = container
        # (connecting retries until RabbitMQ answers: the API serves meanwhile)
        starting = asyncio.create_task(container.start())
        yield
        starting.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await starting
        await container.close()

    app = FastAPI(
        title="Balatro Notification Service",
        version="0.1.0",
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.include_router(meta_router)
    return app


logging.basicConfig(level=logging.INFO)
app = create_app()
