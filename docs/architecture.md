## Архитектура MVP платформы мониторинга обращений

### 1. Общая схема
```
Telegram -> Celery beat (poll_telegram) -> Django API -> Ticket -> Celery NLP -> PostgreSQL + Elasticsearch -> REST API -> Angular UI
                                               \
                                                -> Prometheus/логи SLA
```

- **Каналы**: на MVP подключён Telegram (polling), предусмотрен `BaseConnector` для расширения. Для каналов можно параллельно подключать обсуждения (комментарии) через `TELEGRAM_DISCUSSION_CHAT_IDS`, а также личные обращения в бота (`TELEGRAM_ALLOW_DIRECT=1`) с быстрыми кнопками для выбора типа обращения.
- **Очереди**: Redis используется Celery как брокер и backend результатов.
- **Backend**: Django + DRF реализуют CRUD тикетов, аналитические и поисковые API, Celery обслуживает классификацию и SLA.
- **Хранилища**: PostgreSQL — транзакционный контур, Elasticsearch — быстрый поиск по обращениям, Redis — брокер Celery.
- **Frontend**: Angular SPA (Material + ngx-charts) обеспечивает единое окно мониторинга.
- **ML/AI**: `routing.ai.TransportIntentModel` — компактная нейросеть (embedding + ReLU) на NumPy, определяет транспортную тематику и тональность текста.

### 2. Основные приложения Django
| App        | Ответственность |
|------------|-----------------|
| `tickets`  | Модели `Ticket`, `ChannelMessage`, `Assignment`, административный CRUD. |
| `ingestion`| Коннекторы каналов, Celery задача `poll_telegram`, сохранение `ChannelMessage`. |
| `routing`  | NLP (`KeywordClassifier`), Celery `classify_message`, SLA watchdog, интеграция с аналитикой. |
| `analytics`| Индексация в Elasticsearch и расчёт MTTA/MTTR. |
| `tickets.services` | Сервис `TicketResponseService`, каналы отправки (`OutboundChannel`, `TelegramChannel`). |

### 3. Взаимодействие компонентов
1. `ingestion.tasks.poll_telegram` запрашивает Telegram Bot API, сохраняет `ChannelMessage`, планирует Celery `classify_message`. Помимо основной ленты каналов обрабатываются комментарии из связанных обсуждений (`TELEGRAM_DISCUSSION_CHAT_IDS`) и личные обращения пользователей к боту (при `TELEGRAM_ALLOW_DIRECT=1` бот отправляет приветствие и клавиатуру).
2. `routing.tasks.classify_message` определяет категорию/приоритет/группу, создаёт `Ticket`, индексирует его в Elasticsearch.
3. `routing.tasks.sla_watchdog` отслеживает дедлайны и пишет предупреждения в логи (можно собирать Prometheus).
4. `tickets.services.TicketResponseService` формирует ответы и публикует их в Telegram как reply на исходный комментарий.
5. REST API (`monolith/api`) отдаёт данные фронту; Angular отображает таблицы, графики и позволяет подтверждать/закрывать тикеты и отвечать пассажирам.

### 4. Наблюдаемость и качество
- Prometheus middleware собирает метрики Django/Celery; SLA нарушения логируются и могут экспортироваться в метрики.
- `/api/analytics/metrics` возвращает MTTA/MTTR, долю транспортных обращений и разбивку по тональности для фронтенда.
- Тесты: `pytest` с factory fixtures для `tickets`, unit-тест классификатора `routing`.
- Документация API через `drf-spectacular` (`/api/docs/`).

### 5. Развёртывание
- `docker-compose.yml` описывает сервисы backend, frontend, PostgreSQL, Redis, Elasticsearch и процессы Celery.
- `Makefile` автоматизирует запуск, миграции и тесты.
- Конфигурация переменных вынесена в `config/env.example` (копировать в `.env`).

### 6. Безопасность и интеграции
- Телеграм токен и chat_id берутся из `.env`.
- ESIA / AppFollow / доп. каналы подключаются через расширение `BaseConnector` и отдельные настройки в `.env`.

### 7. Планы развития
- Заменить polling на webhooks + подписки.
- Подключить ML-модель (fastText/BERT) и обучение на исторических данных.
- Реализовать real-time WebSocket/SSE адаптер на базе Redis Streams или другого брокера.
- Добавить агрегирование похожих обращений и автоматические runbook-и для критических инцидентов.
- Реализовать коннекторы для VK/email и переиспользовать `OutboundChannel` для двусторонних коммуникаций.

