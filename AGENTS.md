# AGENTS.md

Rules for anyone, human or agent, changing this repository. `README.md` and
`docs/` describe the service; this file says how to work on it.

## What this project is

The notification service of Balatro in the browser. It consumes the messages
other services publish to RabbitMQ (exchange `notifications`) and sends the
emails. Today that means the identity service's (BalatroIndentityService)
confirmation codes. It is built like the identity service: FastAPI, clean
architecture, uv, ruff, `mypy --strict`.

## Non-negotiable rules

1. **The messages are a contract.** `docs/messages.md` and
   `app/presentation/messaging/schemas.py` describe what publishers send.
   Never rename, remove or change the meaning of a field within a version. A
   breaking change is a new `version`, accepted next to the old one. Change
   the publisher (the identity service's
   `app/infrastructure/notifications/rabbitmq.py`) and its test in the same
   change.
2. **Temporary or permanent, never neither.** Every failure raises
   `DeliveryFailed` (retried) or `InvalidMessage` (set aside). Don't swallow
   errors: a message is acknowledged only once it is handled, dropped on
   purpose (an expired code), or set aside.
3. **Don't leak codes.** Codes appear only in the email. The console backend
   prints them; it is for development only. `ConfirmationCode` hides its value
   in `repr`. Log message ids, not contents.
4. **The topology is this service's.** It declares its exchanges and queues;
   publishers declare only `notifications`. Changing a queue's arguments
   (TTL, dead-letter exchange) needs the queue deleted on every broker first:
   say so in the change.
5. **Escape what goes in HTML.** Templates are `string.Template`; the renderer
   escapes every value for the HTML part.

## Architecture

```
domain  <-  application  <-  infrastructure, presentation  <-  bootstrap, main
```

[docs/architecture.md](docs/architecture.md) describes the layers, the queues
and the reasons behind the design. `tests/test_architecture.py` enforces the
import rules (and keeps FastAPI, pydantic, aio-pika and smtplib out of the
domain and application). Fix the code, not the test.

## Adding a kind of notification

See "Adding a kind of message" in [docs/messages.md](docs/messages.md): a
schema, a use case, a template, the handler, a routing key, the docs, and
tests.

## Commands

```
make install        # uv sync
make rabbitmq       # RabbitMQ from ../BalatroFrontEnd/docker-compose.yml
make run            # consume, health on :8002
make check          # ruff format --check, ruff, mypy, pytest (CI runs this)
make test-rabbitmq  # the consumer against a throwaway RabbitMQ
```

`make check` must pass before committing (and `make test-rabbitmq` after
changing the consumer or the topology). Don't commit or push unless asked.
The branches are `dev` (work) and `main` (deployed by CI).
