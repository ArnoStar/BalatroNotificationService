# BalatroNotificationService: `make` lists the commands.
#
# Alone:        make install && make rabbitmq && make run   (http://localhost:8002/health)
# Everything:   make dev in ../BalatroFrontEnd (the whole site, each part from its repository)
.DEFAULT_GOAL := help
.PHONY: help install rabbitmq run format check test test-rabbitmq docker

# the whole game's compose file (BalatroFrontEnd), which has RabbitMQ and Mailpit
STACK := ../BalatroFrontEnd/docker-compose.yml
PORT ?= 8002
# a throwaway RabbitMQ for test-rabbitmq (its queues are deleted)
TEST_RABBITMQ ?= amqp://guest:guest@127.0.0.1:56720/

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

install: ## dependencies
	uv sync

rabbitmq: ## RabbitMQ (:5672, UI :15672) in Docker, for `make run`
	docker compose -f $(STACK) up -d --wait rabbitmq

run: ## consume the queue, health on http://localhost:8002/health (reloads on changes)
	uv run uvicorn app.main:app --reload --port $(PORT)

format: ## format and fix what can be fixed
	uv run ruff format .
	uv run ruff check . --fix

check: ## what CI runs (ruff format, ruff, mypy, pytest; the RabbitMQ tests skip)
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest

test: ## the tests
	uv run pytest

test-rabbitmq: ## the consumer against a throwaway RabbitMQ (started and removed here)
	docker run -d --rm --name notification-test-rabbitmq -p 127.0.0.1:56720:5672 rabbitmq:4.1-alpine > /dev/null
	@# (asking RabbitMQ before it made its cookie file makes it with the wrong owner,
	@# and the broker stops: wait for the file first)
	@for i in $$(seq 60); do docker exec notification-test-rabbitmq sh -c 'test -f /var/lib/rabbitmq/.erlang.cookie && rabbitmq-diagnostics -q check_port_connectivity' > /dev/null 2>&1 && break; sleep 1; done
	RABBITMQ_TEST_URL=$(TEST_RABBITMQ) uv run pytest -m rabbitmq; status=$$?; \
	docker stop notification-test-rabbitmq > /dev/null; exit $$status

docker: ## this service in Docker, from the game's compose file
	docker compose -f $(STACK) up -d --build --wait notification
