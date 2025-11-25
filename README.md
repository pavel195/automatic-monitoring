# MVP платформы мониторинга обращений пассажиров

Платформа собирает обращения из Telegram, автоматически классифицирует и отображает в едином окне. Стек: Django + Celery + PostgreSQL + Redis + Elasticsearch + Angular.

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
make down        # остановить окружение
```

## Структура
- `backend/` — Django проект `monolith` с приложениями `tickets`, `ingestion`, `routing`, `analytics`.
- `backend/routing/ai` — компактная нейросеть `TransportIntentModel` для темы транспорта и тональности.
- `frontend/monitoring-ui` — Angular SPA (Material + ngx-charts).
- `docs/architecture.md` — детальное описание архитектуры и потоков данных.
- `docker-compose.yml` — Сервисы: backend, Celery worker/beat, PostgreSQL, Redis, Elasticsearch, frontend.

## Поток обработки
1. `ingestion.tasks.poll_telegram` опрашивает Telegram (credentials берутся из `.env`), сохраняет сообщения в БД и ставит Celery-задачу классификации. Offset хранится в Redis, поэтому дубликатов нет.
2. `routing.KeywordClassifier` назначает тип/приоритет/группу, создаёт `Ticket`, индексирует его в Elasticsearch.
3. `routing.sla_watchdog` отслеживает дедлайны SLA и пишет предупреждения в логи/метрики.
4. `tickets.services.TicketResponseService` публикует ответы операторов обратно в Telegram (reply на исходный комментарий), статус сохраняется в `TicketResponse`.
5. Angular UI вызывает REST API (`/api/tickets`, `/api/analytics/metrics`, `/api/search`, `/api/tickets/{id}/respond/`), визуализирует MTTA/MTTR, долю транспортных обращений, распределение по тональности и позволяет подтверждать/закрывать тикеты и отвечать пассажирам прямо из окна обращений.

## Тесты и качество
- `pytest` + `factory-boy` для доменной логики (`tickets/tests`, `routing/tests`).
- `drf-spectacular` публикует Swagger по `/api/docs/`.
- `django-prometheus` добавляет метрики MTTA/MTTR и статусы Celery.

## Дальнейшие шаги
- Добавить real-time канал оповещений (WebSocket/SSE) поверх Redis Streams или другого брокера.
- Обучить ML модель на исторических обращениях и заменить baseline.
- Подключить VK, email и магазины приложений через новых наследников `BaseConnector`.
- Расширить `OutboundChannel` дополнительными каналами (email, AppFollow) и добавить SLA по времени ответа.

