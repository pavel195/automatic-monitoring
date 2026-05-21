"""Классификатор на основе локальной LLM (Ollama).

Отправляет структурированный промпт на русском языке,
ожидает JSON-ответ с полями классификации.
При ошибке или недоступности Ollama — graceful fallback на KeywordClassifier.
"""

import json
import logging
import re

import requests
from django.conf import settings

from routing.nlp_classifier import ClassificationResult, KeywordClassifier
from tickets.models import Sentiment, TransportMode

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """Ты — система классификации обращений пассажиров общественного транспорта.
Проанализируй текст обращения и верни JSON с полями:

- "category": одно из ["complaint", "praise", "request", "incident", "suggestion", "payment"]
- "priority": число от 1 до 4 (1=низкий, 2=средний, 3=высокий, 4=критический)
- "sentiment": одно из ["positive", "neutral", "negative"]
- "transport_mode": одно из ["metro", "bus", "tram", "train", "airplane", "water", "taxi", "other"]
- "is_transport": true если обращение связано с транспортом, иначе false
- "group": одно из ["operations", "safety", "service", "maintenance"]
- "title": краткое название обращения (до 120 символов, на русском)

Правила:
- incident (инцидент): аварии, травмы, пожары, угрозы безопасности → priority 4
- complaint (жалоба): недовольство сервисом, задержки, грубость → priority 2-3
- praise (благодарность): положительные отзывы → priority 1
- request (запрос): вопросы, запросы информации → priority 1-2
- suggestion (предложение): идеи по улучшению → priority 1
- payment (оплата): вопросы оплаты, возвраты → priority 2

Верни ТОЛЬКО валидный JSON, без пояснений.

Текст обращения:
"""

VALID_CATEGORIES = {"complaint", "praise", "request", "incident", "suggestion", "payment"}
VALID_SENTIMENTS = {"positive", "neutral", "negative"}
VALID_TRANSPORT_MODES = {m.value for m in TransportMode}
VALID_GROUPS = {"operations", "safety", "service", "maintenance"}


class OllamaClassifier:
    """Классификатор через Ollama REST API."""

    def __init__(self):
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", "http://ollama:11434")
        self.model = getattr(settings, "OLLAMA_MODEL", "llama3.2:3b")
        self.timeout = getattr(settings, "OLLAMA_TIMEOUT", 30)
        self.enabled = getattr(settings, "OLLAMA_ENABLED", True)
        self.session = requests.Session()

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            resp = self.session.get(
                f"{self.base_url}/api/tags",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def classify(self, text: str) -> dict:
        """Классифицирует текст через Ollama. Возвращает dict с полями классификации."""
        prompt = CLASSIFICATION_PROMPT + text

        resp = self.session.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 256,
                },
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()

        raw = resp.json().get("response", "")
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        """Извлекает JSON из ответа LLM."""
        # Попытка найти JSON в ответе
        json_match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = json.loads(raw)

        # Валидация и нормализация
        result = {}
        result["category"] = data.get("category", "request")
        if result["category"] not in VALID_CATEGORIES:
            result["category"] = "request"

        result["priority"] = data.get("priority", 2)
        if not isinstance(result["priority"], int) or result["priority"] not in range(1, 5):
            result["priority"] = 2

        result["sentiment"] = data.get("sentiment", "neutral")
        if result["sentiment"] not in VALID_SENTIMENTS:
            result["sentiment"] = "neutral"

        result["transport_mode"] = data.get("transport_mode", "other")
        if result["transport_mode"] not in VALID_TRANSPORT_MODES:
            result["transport_mode"] = "other"

        result["is_transport"] = bool(data.get("is_transport", False))

        result["group"] = data.get("group", "operations")
        if result["group"] not in VALID_GROUPS:
            result["group"] = "operations"

        title = data.get("title", "")
        result["title"] = str(title)[:120] if title else ""

        return result


class HybridClassifier:
    """Гибридный классификатор: Ollama с fallback на KeywordClassifier."""

    def __init__(self):
        self.llm = OllamaClassifier()
        self.keyword = KeywordClassifier()

    def classify(self, text: str) -> tuple:
        """Возвращает (ClassificationResult, sentiment, is_transport, transport_mode, source).

        source: 'llm' или 'keyword'
        """
        # Пробуем LLM
        if self.llm.enabled:
            try:
                data = self.llm.classify(text)
                cr = ClassificationResult(
                    category=data["category"],
                    priority=data["priority"],
                    group=data["group"],
                    title=data["title"] or self.keyword._extract_title(text.lower()),
                )
                sentiment = Sentiment(data["sentiment"])
                is_transport = data["is_transport"]
                transport_mode = TransportMode(data["transport_mode"])
                logger.info("[LLM] Классификация через Ollama: %s", data["category"])
                return cr, sentiment, is_transport, transport_mode, "llm"
            except Exception as e:
                logger.warning("[LLM] Ollama недоступна или ошибка: %s. Fallback на keywords.", e)

        # Fallback на keyword
        from routing.ai.transport_intent import TransportIntentModel
        cr = self.keyword.predict(text)
        intent_model = TransportIntentModel()
        intent = intent_model.predict(text)
        logger.info("[KEYWORD] Классификация через keywords: %s", cr.category)
        return cr, intent.sentiment, intent.is_transport, intent.transport_mode, "keyword"
