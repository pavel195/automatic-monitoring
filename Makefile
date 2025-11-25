DOCKER_COMPOSE = docker compose -f docker-compose.yml --project-name transport

.PHONY: up down logs migrate shell backend tests collectstatic consumer

up:
	$(DOCKER_COMPOSE) up -d --build

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

migrate:
	$(DOCKER_COMPOSE) run --rm backend python manage.py migrate

shell:
	$(DOCKER_COMPOSE) run --rm backend python manage.py shell

backend:
	$(DOCKER_COMPOSE) run --rm backend sh

tests:
	$(DOCKER_COMPOSE) run --rm backend pytest

collectstatic:
	$(DOCKER_COMPOSE) run --rm backend python manage.py collectstatic --noinput

consumer:
	$(DOCKER_COMPOSE) run --rm backend python manage.py run_kafka_consumer

