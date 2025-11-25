## Архитектура MVP платформы мониторинга обращений

### 1. Общая схема
```
Telegram -> Ingestion (Celery beat) -> Kafka raw_messages -> Django consumer -> Ticket -> Celery NLP -> PostgreSQL + Elasticsearch -> REST API -> Angular UI
                                                                         \-> Kafka alerts -> Flower/SLA
```

- **Каналы**: на MVP подключён Telegram (polling), предусмотрен `BaseConnector` для расширения.
- **Шина**: Kafka принимает нормализованные события (`raw_messages`, `alerts`).
- **Backend**: Django + DRF реализуют CRUD тикетов, аналитические и поисковые API, Celery обслуживает классификацию и SLA.
- **Хранилища**: PostgreSQL — транзакционный контур, Elasticsearch — быстрый поиск по обращениям, Redis — брокер Celery, Kafka — потоковая шина.
- **Frontend**: Angular SPA (Material + ngx-charts) обеспечивает единое окно мониторинга.

### 2. Основные приложения Django
| App        | Ответственность |
|------------|-----------------|
| `tickets`  | Модели `Ticket`, `ChannelMessage`, `Assignment`, административный CRUD. |
| `ingestion`| Коннекторы каналов, Kafka producer, Celery задача `poll_telegram`. |
| `routing`  | NLP (`KeywordClassifier`), Celery `classify_message`, SLA watchdog, интеграция с Kafka alerts. |
| `analytics`| Индексация в Elasticsearch и расчёт MTTA/MTTR. |

### 3. Взаимодействие компонентов
1. `ingestion.tasks.poll_telegram` запрашивает Telegram Bot API, публикует события в Kafka (`RawMessageProducer`).
2. `RawMessageConsumer` (запускается как management-команда или отдельный процесс) читает `raw_messages`, сохраняет `ChannelMessage`, планирует Celery `classify_message`.
3. `routing.tasks.classify_message` определяет категорию/приоритет/группу, создаёт `Ticket`, индексирует его в Elasticsearch и отправляет уведомление в Kafka `alerts`.
4. `routing.tasks.sla_watchdog` отслеживает дедлайны и шлёт `sla_ack_breach`.
5. REST API (`monolith/api`) отдаёт данные фронту; Angular отображает таблицы, графики и управляет статусами тикетов.

### 4. Наблюдаемость и качество
- Prometheus middleware собирает метрики Django/Celery; Kafka topics фиксируют события SLA.
- Тесты: `pytest` с factory fixtures для `tickets`, unit-тест классификатора `routing`.
- Документация API через `drf-spectacular` (`/api/docs/`).

### 5. Развёртывание
- `docker-compose.yml` описывает все сервисы (backend, frontend, PostgreSQL, Redis, Kafka, Zookeeper, Elasticsearch, Kibana, Celery worker/beat, Flower).
- `Makefile` автоматизирует запуск, миграции и тесты.
- Конфигурация переменных вынесена в `config/env.example` (копировать в `.env`).

### 6. Безопасность и интеграции
- Телеграм токен и chat_id берутся из `.env`.
- ESIA / AppFollow / доп. каналы подключаются через расширение `BaseConnector` и отдельные настройки в `.env`.

### 7. Планы развития
- Заменить polling на webhooks + подписки.
- Подключить ML-модель (fastText/BERT) и обучение на исторических данных.
- Реализовать real-time WebSocket/SSE адаптер на базе Kafka `alerts`.
- Добавить агрегирование похожих обращений и автоматические runbook-и для критических инцидентов.

