# Balatro Notification Service

Sends Balatro's emails. The other services don't send email themselves: they
publish a message to RabbitMQ saying what happened ("this player needs this
code"), and this service writes the email from its templates and sends it.

For now there is one kind of message: the identity service's **confirmation
codes**, to confirm an email address or to reset a password.

```
identity service ──(email.confirmation_code)──► RabbitMQ ──► notification service ──SMTP──► inbox
                                                 "notifications" exchange          (or the log, in development)
```

- The identity service doesn't wait for the mail server, and a mail server
  that is down doesn't lose codes: messages wait, and are retried.
- The words and the look of the emails are in one place
  (`app/infrastructure/templates/`).
- New notifications (welcome, a duel invitation, a leaderboard result) are a
  new message type here. The other services only publish.

It is a FastAPI application in clean architecture, like the identity service.
The HTTP API only reports its health; the work is done by the queue consumer
it runs.

| | |
|---|---|
| [docs/messages.md](docs/messages.md) | the messages other services send (the contract), and how to publish one |
| [docs/architecture.md](docs/architecture.md) | the layers, the queues, retries, and the decisions behind them |
| [AGENTS.md](AGENTS.md) | the rules for changing this repository |

## Run it

You need Python 3.13, [uv](https://docs.astral.sh/uv/) and Docker (for RabbitMQ).

```
make install          # dependencies
make rabbitmq         # RabbitMQ in Docker (from the game's compose file): :5672, UI :15672
make run              # consumes; health at http://localhost:8002/health
```

With the default `EMAIL_BACKEND=console`, the emails' text goes to the log.
For a real inbox in development, start Mailpit (`docker compose --profile mail
up -d mailpit` in BalatroFrontEnd) and run with `EMAIL_BACKEND=smtp
SMTP_HOST=localhost SMTP_PORT=1025 SMTP_SECURITY=none`. The emails, text and
HTML, then appear at http://localhost:8025.

To see the identity service use it, run it with `EMAIL_BACKEND=notifications`
(its `.env`). BalatroFrontEnd's `make dev` does all of that: it runs the whole
site, this service included, from the repositories.

## Configuration

Environment variables, or lines of a `.env` file ([.env.example](.env.example)):

| Variable | Default | |
|---|---|---|
| `RABBITMQ_URL` | `amqp://balatro:balatro@localhost:5672/` | the compose file's RabbitMQ |
| `RABBITMQ_PREFETCH` | `10` | messages handled at the same time |
| `RETRY_DELAY_SECONDS` / `MAX_ATTEMPTS` | `30` / `5` | a delivery that failed for now waits, then is tried again; after the last attempt the message is set aside |
| `EMAIL_BACKEND` | `console` | `console` (the log) or `smtp` |
| `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_SECURITY` | | `SMTP_SECURITY`: `starttls` (587), `ssl` (465) or `none` |
| `SITE_NAME` / `SITE_URL` | `Balatro` / `http://localhost:5174` | in the emails (the link is the portal) |

In the Docker stack, these come from BalatroFrontEnd's `.env`: `EMAIL_BACKEND`,
`EMAIL_FROM`, the `SMTP_*` settings and `RABBITMQ_PASSWORD`. `SITE_URL` is
`PUBLIC_URL`.

## Checks

```
make check            # ruff format --check, ruff, mypy --strict, pytest
make test-rabbitmq    # the consumer against a throwaway RabbitMQ (Docker)
```

`make check` uses fakes (an outbox, a fixed clock) and needs no services. The
RabbitMQ tests publish real messages and check retries and the failed queue.
They are skipped unless `RABBITMQ_TEST_URL` is set; CI runs them with a
RabbitMQ service.

## When something fails

- **The mail server is down**: each message is retried every
  `RETRY_DELAY_SECONDS`, `MAX_ATTEMPTS` times, then set aside. A code that
  expired meanwhile is dropped, not sent: it wouldn't work.
- **A message is set aside** (invalid, or failed every attempt): it is in the
  `notification.email.failed` queue, with headers `x-failure-reason` and
  `x-original-routing-key`. RabbitMQ's management UI shows it (Queues →
  `notification.email.failed` → Get messages). To send it again, move it
  (*Move messages* in the UI, with the shovel plugin) to the `notifications`
  exchange with its original routing key.
- **This service isn't running**: the identity service's publish is refused
  (nothing is bound to the exchange), so it answers 503 `email_delivery_failed`
  and the player asks for a new code. When the service is up, messages wait in
  its queue even while it restarts.

## Deployment

`.github/workflows/ci-cd.yml` checks every push and pull request on `main` and
`dev`: the checks, the RabbitMQ tests, and the Docker image. A push to `main`
deploys like the other repositories: `.github/deploy.sh` copies the code to
`DEPLOY_PATH/BalatroNotificationService`, and BalatroFrontEnd's
`docker-compose.yml` rebuilds the `notification` service. It uses the same
`DEPLOY_*` secrets. On the server, the email settings go in
`/opt/balatro/BalatroFrontEnd/.env` (`EMAIL_BACKEND=smtp`, `SMTP_*`,
`EMAIL_FROM`, `RABBITMQ_PASSWORD`).
