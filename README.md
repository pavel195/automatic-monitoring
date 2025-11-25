# MVP платформы мониторинга обращений пассажиров

Платформа собирает обращения из Telegram, нормализует через Kafka, автоматически классифицирует и отображает в едином окне. Стек: Django + Celery + PostgreSQL + Kafka + Elasticsearch + Angular.

## Быстрый старт
```bash
cp config/env.example .env   # .env нужно создать вручную (файл в корне заблокирован системой)
make up
make migrate
```

Полезные команды:
```bash
make logs        # посмотреть логи всех сервисов
make tests       # backend pytest
make shell       # Django shell
make consumer    # Kafka consumer (ingestion)
make down        # остановить окружение
```

## Структура
- `backend/` — Django проект `monolith` с приложениями `tickets`, `ingestion`, `routing`, `analytics`.
- `frontend/monitoring-ui` — Angular SPA (Material + ngx-charts).
- `docs/architecture.md` — детальное описание архитектуры и потоков данных.
- `docker-compose.yml` — Сервисы: backend, Celery worker/beat, Flower, PostgreSQL, Redis, Kafka, Zookeeper, Elasticsearch, Kibana, frontend.

## Поток обработки
1. `ingestion.tasks.poll_telegram` опрашивает Telegram (credentials берутся из `.env`), кладёт сообщения в Kafka topic `raw_messages`.
2. `ingestion.RawMessageConsumer` создаёт `ChannelMessage` и очередь Celery `classify_message`.
3. `routing.KeywordClassifier` назначает тип/приоритет/группу, создаёт `Ticket`, индексирует его в Elasticsearch и публикует событие `alerts`.
4. `routing.sla_watchdog` отслеживает дедлайны SLA и отправляет нарушения в Kafka.
5. Angular UI вызывает REST API (`/api/tickets`, `/api/analytics/metrics`, `/api/search`) и визуализирует MTTA/MTTR, статусы и графики.

## Тесты и качество
- `pytest` + `factory-boy` для доменной логики (`tickets/tests`, `routing/tests`).
- `drf-spectacular` публикует Swagger по `/api/docs/`.
- `django-prometheus` добавляет метрики MTTA/MTTR и статусы Celery.

## Дальнейшие шаги
- Добавить consumer для реального времени (SSE/WebSocket) поверх Kafka `alerts`.
- Обучить ML модель на исторических обращениях и заменить baseline.
- Подключить VK, email и магазины приложений через новых наследников `BaseConnector`.

