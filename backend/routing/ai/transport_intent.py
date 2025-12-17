import re
from dataclasses import dataclass
from typing import Dict, Iterable

import numpy as np

from tickets.models import Sentiment, TransportMode


@dataclass
class IntentPrediction:
    is_transport: bool
    transport_score: float
    sentiment: str
    sentiment_scores: Dict[str, float]
    transport_mode: str


class TransportIntentModel:
    """Миниатюрная нейросеть (embedding -> ReLU -> classifier) для фильтрации тематики и тона."""

    def __init__(self):
        self.token_pattern = re.compile(r"[а-яa-z0-9]+", re.IGNORECASE)
        self.vocab = {
            # Транспорт
            "поезд": 0,
            "жд": 1,
            "метро": 2,
            "трамвай": 3,
            "автобус": 4,
            "самолет": 5,
            "маршрут": 6,
            "рейс": 7,
            "электричк": 8,
            "ласточк": 9,
            "сапсан": 10,
            "маршрутк": 11,
            "такси": 12,
            "паром": 13,
            "теплоход": 14,
            "перрон": 15,
            "вокзал": 16,
            "станц": 17,
            "остановк": 18,
            "платформ": 19,
            # Не транспорт
            "еда": 20,
            "магазин": 21,
            "парикмахер": 22,
            "ресторан": 23,
            "кафе": 24,
            # Эмоции позитивные
            "классно": 25,
            "спасибо": 26,
            "отлично": 27,
            "замечательно": 28,
            "прекрасно": 29,
            "благодар": 30,
            "доволен": 31,
            "нравится": 32,
            "люблю": 33,
            # Эмоции негативные
            "ужас": 34,
            "задержка": 35,
            "проблема": 36,
            "плохо": 37,
            "недоволен": 38,
            "неприятно": 39,
            "разочарован": 40,
            "кошмар": 41,
            "неудобно": 42,
            "не работает": 43,
            "опоздан": 44,
            "слом": 45,
        }
        embed_dim = 8  # Увеличиваем размерность для лучшего представления
        rng = np.random.default_rng(42)
        base_embeddings = rng.uniform(-1, 1, (len(self.vocab), embed_dim))
        # усиливаем транспортные токены
        transport_boost = np.array([1.2, 0.8, 1.0, 0.6, 1.1, 0.9, 0.7, 0.8])
        transport_tokens = [
            "поезд", "жд", "метро", "трамвай", "автобус", "самолет",
            "маршрут", "рейс", "электричк", "ласточк", "сапсан",
            "маршрутк", "такси", "паром", "теплоход", "перрон",
            "вокзал", "станц", "остановк", "платформ"
        ]
        for token in transport_tokens:
            if token in self.vocab:
                base_embeddings[self.vocab[token]] += transport_boost
        # усиливаем негатив
        negative_boost = np.array([-1.5, -1.0, -0.5, -0.2, -0.1, -0.3, -0.4, -0.2])
        for token in ["ужас", "задержка", "проблема", "плохо", "недоволен",
                      "неприятно", "разочарован", "кошмар", "неудобно",
                      "не работает", "опоздан", "слом"]:
            if token in self.vocab:
                base_embeddings[self.vocab[token]] += negative_boost
        # усиливаем позитив
        positive_boost = np.array([0.8, 0.6, 0.9, 0.4, 0.3, 0.2, 0.5, 0.4])
        for token in ["спасибо", "классно", "отлично", "замечательно",
                      "прекрасно", "благодар", "доволен", "нравится", "люблю"]:
            if token in self.vocab:
                base_embeddings[self.vocab[token]] += positive_boost
        self.embeddings = base_embeddings.astype(np.float32)

        hidden_dim = 12  # Увеличиваем для лучшей обработки
        self.W1 = rng.uniform(-0.8, 0.8, (hidden_dim, embed_dim)).astype(np.float32)
        self.b1 = rng.uniform(-0.2, 0.2, hidden_dim).astype(np.float32)

        self.W_transport = rng.uniform(-0.5, 0.5, hidden_dim).astype(np.float32)
        # bias сдвигает решение в сторону "не транспорт"
        self.b_transport = np.float32(-0.3)

        self.sentiment_labels = [
            Sentiment.NEGATIVE,
            Sentiment.NEUTRAL,
            Sentiment.POSITIVE,
        ]
        self.W_sentiment = rng.uniform(-0.6, 0.6, (len(self.sentiment_labels), hidden_dim)).astype(
            np.float32
        )
        self.b_sentiment = np.zeros(len(self.sentiment_labels), dtype=np.float32)

        self.transport_keywords = {
            # Общие транспортные термины
            "поезд", "жд", "метро", "трамвай", "автобус", "маршрут",
            "рейс", "самолет", "перрон", "путевка", "рейсовый",
            "электричк", "ласточк", "сапсан", "маршрутк", "такси",
            "паром", "теплоход", "вокзал", "станц", "остановк",
            "платформ", "транспорт", "проезд", "билет", "проездн",
            "рейсов", "маршрутн", "движен", "график", "расписан",
            # Дополнительные термины
            "поездк", "поездка", "перевозк", "перевозка", "транспортировк",
            "пассажир", "пассажирск", "пассажирский", "пассажиры",
            "вагон", "вагоны", "состав", "поездной состав",
            "локомотив", "машинист", "проводник", "кондуктор",
            "автовокзал", "железнодорожн", "железнодорожный",
            "пригородн", "пригородный", "дальн", "дальний",
            "скорый", "скорый поезд", "пассажирский поезд",
            "электричк", "электричка", "пригородная электричка",
            "ласточк", "ласточка", "сапсан", "скорый поезд сапсан",
            "автобусн", "автобусный", "автобусы", "автобусная остановка",
            "маршрутк", "маршрутка", "маршрутное такси",
            "троллейбус", "троллейб", "троллейбусный",
            "метрополитен", "подземк", "подземка", "подземный",
            "мцк", "мцд", "московское центральное кольцо",
            "аэропорт", "авиа", "авиационн", "авиационный",
            "рейс", "авиарейс", "борт", "самолетн", "самолетный",
            "паром", "паромн", "паромный", "теплоход", "судно",
            "лодк", "лодка", "катер", "водн", "водный",
            "речн", "речной", "морск", "морской",
            "такси", "такс", "таксист", "таксопарк",
            "яндекс такси", "uber", "болт", "делимобил",
            "проездной", "проездной билет", "транспортная карта",
            "транспортн", "транспортный", "общественный транспорт",
        }
        self.mode_keywords = {
            TransportMode.METRO: {
                "метро", "метрополитен", "мцк", "мцд", "подземк",
                "подземн", "подземка", "линия", "ветк", "ветка метро",
                "линия метро", "станция метро", "московское метро",
                "подземный транспорт",
            },
            TransportMode.BUS: {
                "автобус", "маршрутк", "пазик", "шаттл", "автобусн",
                "автобусы", "маршрутн", "рейсовый автобус", "автобусный",
                "автобусная остановка", "автобусный маршрут",
                "городской автобус", "пригородный автобус",
            },
            TransportMode.TRAM: {
                "трамвай", "трам", "троллейб", "троллейбус",
                "трамвайн", "трамваи", "трамвайный", "трамвайная линия",
                "городской трамвай", "трамвайная остановка",
            },
            TransportMode.TRAIN: {
                "поезд", "жд", "электричк", "ласточк", "сапсан",
                "поездн", "железнодорожн", "железнодорожный",
                "пригородн", "пригородный", "дальн", "дальний",
                "скорый", "скорый поезд", "пассажирский поезд",
                "электричка", "пригородная электричка",
                "ласточка", "вагон", "состав", "локомотив",
                "проводник", "машинист",
            },
            TransportMode.AIRPLANE: {
                "самолет", "аэропорт", "борд", "рейс", "авиа",
                "авиационн", "авиационный", "самолетн", "самолетный",
                "авиакомпани", "авиакомпания", "авиарейс",
                "авиаперевозк", "авиаперевозка", "полет",
            },
            TransportMode.WATER: {
                "паром", "теплоход", "судно", "лодк", "лодка",
                "водн", "водный", "речн", "речной", "морск", "морской",
                "паромн", "паромный", "катер", "яхт",
            },
            TransportMode.TAXI: {
                "такси", "яндекс", "uber", "болт", "делимобил",
                "такс", "таксист", "таксопарк", "такси служба",
                "яндекс такси", "заказ такси", "вызов такси",
            },
        }
        self.positive_lexeme = {
            # Благодарности
            "спасибо", "благодар", "благодарю", "благодарность", "благодарност",
            "признателен", "признательн", "благодарен", "благодарн",
            # Позитивные эмоции
            "классно", "отлично", "замечательно", "прекрасно", "великолепно",
            "супер", "хорошо", "отличн", "замечательн", "прекрасн",
            "восхищен", "восхищаюсь", "в восторге", "восторг",
            "доволен", "довольн", "удовлетворен", "удовлетворительн",
            "нравится", "нравит", "люблю", "любим", "любит",
            "рекомендую", "рекоменд", "советую", "совет",
            "молодцы", "молодец", "хвалю", "хвалят", "похвальн",
            # Позитивные оценки
            "качественн", "качественно", "профессиональн", "профессионально",
            "вежлив", "вежливо", "приятн", "приятно", "комфортн", "комфортно",
            "удобн", "удобно", "чист", "чисто", "аккуратн", "аккуратно",
            "пунктуальн", "пунктуально", "быстро", "быстр",
        }
        self.negative_lexeme = {
            # Негативные эмоции
            "ужас", "ужасно", "кошмар", "кошмарн", "наплевать",
            "плохо", "плох", "плохое", "плохая", "плохой",
            "недоволен", "недовольн", "недовольство", "недовольств",
            "неприятно", "неприятн", "неприятность", "неприятност",
            "разочарован", "разочарованн", "разочарование", "разочарован",
            "возмущен", "возмущенн", "возмущение", "возмущен",
            # Проблемы и сбои
            "задержка", "задержк", "задерж", "опоздан", "опоздал", "опоздал",
            "не работает", "не работает", "слом", "сломал", "сломан", "слома",
            "поломк", "поломка", "поломан", "неисправн", "неисправно",
            "проблем", "проблема", "проблемы", "проблемн",
            "неудобно", "неудобн", "неудобство", "неудобств",
            "некачественно", "некачественн", "некачественное",
            "неприемлемо", "неприемлем", "неприемлемое",
            # Конфликты
            "скандал", "скандальн", "конфликт", "конфликтн",
            "негатив", "негативн", "негативное",
            # Дополнительные негативные маркеры
            "грязн", "грязно", "грязь", "вонь", "запах", "мусор",
            "шумн", "шумно", "шум", "холодн", "холодно", "жарк", "жарко",
            "душн", "душно", "тесно", "переполнен", "переполн",
            "давк", "давка", "толп", "толпа", "очеред", "очередь",
            "груб", "грубо", "грубость", "хам", "хамство", "невежлив",
            "невежливо", "некорректн", "некорректно", "неприличн",
            "антисанитар", "антисанитария",
        }

    def predict(self, text: str) -> IntentPrediction:
        tokens = list(self._tokenize(text))
        token_set = set(tokens)
        embedding = self._encode(tokens)
        hidden = np.maximum(0, self.W1 @ embedding + self.b1)

        transport_logit = float(self.W_transport @ hidden + self.b_transport)
        transport_prob = self._sigmoid(transport_logit)

        keyword_hit = any(token in self.transport_keywords for token in token_set)
        if keyword_hit:
            transport_prob = min(1.0, transport_prob + 0.35)
        else:
            transport_prob *= 0.5

        sentiment_logits = self.W_sentiment @ hidden + self.b_sentiment
        sentiment_probs = self._softmax(sentiment_logits)
        sentiment_probs = self._adjust_probs(token_set, sentiment_probs)
        sentiment_idx = int(np.argmax(sentiment_probs))
        sentiment = self.sentiment_labels[sentiment_idx]

        transport_mode = self._detect_mode(token_set)
        if transport_mode != TransportMode.OTHER:
            keyword_hit = True
        elif keyword_hit:
            transport_mode = self._fallback_mode(token_set)

        return IntentPrediction(
            is_transport=keyword_hit or transport_prob >= 0.55,
            transport_score=transport_prob,
            sentiment=sentiment,
            sentiment_scores={
                label: float(prob) for label, prob in zip(self.sentiment_labels, sentiment_probs)
            },
            transport_mode=transport_mode,
        )

    def _tokenize(self, text: str) -> Iterable[str]:
        for match in self.token_pattern.findall(text.lower()):
            yield match

    def _encode(self, tokens: Iterable[str]) -> np.ndarray:
        vectors = [
            self.embeddings[self.vocab[token]]
            for token in tokens
            if token in self.vocab
        ]
        if not vectors:
            return np.zeros(self.embeddings.shape[1], dtype=np.float32)
        stacked = np.stack(vectors)
        return np.mean(stacked, axis=0)

    @staticmethod
    def _sigmoid(x: float) -> float:
        return float(1 / (1 + np.exp(-x)))

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        shifted = logits - np.max(logits)
        exp = np.exp(shifted)
        return exp / np.sum(exp)

    def _adjust_probs(self, tokens: set[str], probs: np.ndarray) -> np.ndarray:
        """Улучшенная корректировка вероятностей тональности на основе ключевых слов."""
        adjusted = probs.copy()
        
        # Подсчитываем количество совпадений для более точной оценки
        positive_matches = len(tokens & self.positive_lexeme)
        negative_matches = len(tokens & self.negative_lexeme)
        
        # Если есть явные маркеры, сильно корректируем вероятности
        if negative_matches > 0:
            # Чем больше негативных маркеров, тем сильнее корректировка
            negative_boost = min(0.4, 0.15 + (negative_matches * 0.05))
            adjusted[0] += negative_boost  # Увеличиваем вероятность негатива
            adjusted[2] -= min(0.2, negative_boost * 0.5)  # Уменьшаем позитив
            adjusted[1] -= min(0.1, negative_boost * 0.25)  # Немного уменьшаем нейтральность
        
        if positive_matches > 0:
            # Чем больше позитивных маркеров, тем сильнее корректировка
            positive_boost = min(0.4, 0.15 + (positive_matches * 0.05))
            adjusted[2] += positive_boost  # Увеличиваем вероятность позитива
            adjusted[0] -= min(0.2, positive_boost * 0.5)  # Уменьшаем негатив
            adjusted[1] -= min(0.1, positive_boost * 0.25)  # Немного уменьшаем нейтральность
        
        # Если есть и позитивные, и негативные маркеры, приоритет у негативных
        if positive_matches > 0 and negative_matches > 0:
            if negative_matches >= positive_matches:
                # Негатив перевешивает
                adjusted[0] += 0.1
                adjusted[2] -= 0.15
            else:
                # Позитив перевешивает, но слабее
                adjusted[2] += 0.05
            adjusted[0] -= 0.1
        
        # Ограничиваем значения и нормализуем
        adjusted = np.clip(adjusted, 0.01, 0.98)
        adjusted = adjusted / np.sum(adjusted)
        
        return adjusted

    def _detect_mode(self, tokens: set[str]) -> str:
        for mode, keywords in self.mode_keywords.items():
            if tokens & keywords:
                return mode
        return TransportMode.OTHER

    def _fallback_mode(self, tokens: set[str]) -> str:
        if {"маршрут", "маршрутк"} & tokens:
            return TransportMode.BUS
        if "рейс" in tokens or "перрон" in tokens:
            return TransportMode.TRAIN
        return TransportMode.OTHER

