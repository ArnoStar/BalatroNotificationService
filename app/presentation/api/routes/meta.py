from fastapi import APIRouter, Request, Response

router = APIRouter(tags=["Meta"])


@router.get("/health", summary="Is the service consuming its queue")
def health(request: Request, response: Response) -> dict[str, str]:
    """503 until it is connected to RabbitMQ and consuming (it retries the
    connection by itself)."""
    consuming = request.app.state.container.consumer.healthy
    if not consuming:
        response.status_code = 503
    return {
        "status": "ok" if consuming else "starting",
        "rabbitmq": "ok" if consuming else "down",
    }
