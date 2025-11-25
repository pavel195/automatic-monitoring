import logging
from typing import Any, Dict

from django.conf import settings
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

INDEX_NAME = "tickets"


def _client() -> Elasticsearch:
    return Elasticsearch(settings.ELASTICSEARCH_HOST)


def index_ticket(ticket) -> None:
    body: Dict[str, Any] = {
        "title": ticket.title,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_group": ticket.assigned_group,
        "ack_deadline": ticket.ack_deadline.isoformat()
        if ticket.ack_deadline
        else None,
        "resolve_deadline": ticket.resolve_deadline.isoformat()
        if ticket.resolve_deadline
        else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }
    try:
        _client().index(index=INDEX_NAME, id=ticket.id, document=body)
    except Exception as exc:  # pragma: no cover
        logger.error("Не удалось проиндексировать тикет %s: %s", ticket.id, exc)


def search_tickets(query: str) -> Dict[str, Any]:
    try:
        response = _client().search(
            index=INDEX_NAME,
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "category", "status"],
                }
            },
        )
        return response
    except Exception as exc:  # pragma: no cover
        logger.error("Ошибка поиска в Elasticsearch: %s", exc)
        return {"hits": {"hits": []}}

