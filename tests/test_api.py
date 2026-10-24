from fastapi.testclient import TestClient

from app.bootstrap.container import Container
from app.infrastructure.config.settings import Settings
from app.main import create_app


class FakeConsumer:
    healthy = False

    async def start(self) -> None:
        self.healthy = True

    async def close(self) -> None:
        self.healthy = False


def test_health_follows_the_consumer() -> None:
    consumer = FakeConsumer()

    def container(settings: Settings) -> Container:
        c = Container(settings)
        c.consumer = consumer  # type: ignore[assignment]
        return c

    app = create_app(Settings(_env_file=None), container)  # type: ignore[call-arg]
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "rabbitmq": "ok"}
        consumer.healthy = False
        response = client.get("/health")
        assert response.status_code == 503
