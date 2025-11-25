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
            "поезд": 0,
            "жд": 1,
            "метро": 2,
            "трамвай": 3,
            "автобус": 4,
            "самолет": 5,
            "маршрут": 6,
            "рейс": 7,
            "еда": 8,
            "магазин": 9,
            "парикмахер": 10,
            "классно": 11,
            "ужас": 12,
            "задержка": 13,
            "спасибо": 14,
            "проблема": 15,
        }
        embed_dim = 6
        rng = np.random.default_rng(42)
        base_embeddings = rng.uniform(-1, 1, (len(self.vocab), embed_dim))
        # усиливаем транспортные токены
        transport_boost = np.array([1.2, 0.8, 1.0, 0.6, 1.1, 0.9])
        for token in ["поезд", "жд", "метро", "трамвай", "автобус", "самолет", "маршрут", "рейс"]:
            base_embeddings[self.vocab[token]] += transport_boost
        # усиливаем негатив / позитив
        base_embeddings[self.vocab["ужас"]] += np.array([-1.5, -1.0, -0.5, -0.2, -0.1, -0.3])
        base_embeddings[self.vocab["задержка"]] += np.array([-1.2, -0.8, -0.5, -0.4, -0.2, -0.2])
        base_embeddings[self.vocab["спасибо"]] += np.array([0.8, 0.6, 0.9, 0.4, 0.3, 0.2])
        base_embeddings[self.vocab["классно"]] += np.array([0.7, 0.5, 0.8, 0.3, 0.2, 0.1])
        self.embeddings = base_embeddings.astype(np.float32)

        hidden_dim = 8
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
            "поезд",
            "жд",
            "метро",
            "трамвай",
            "автобус",
            "маршрут",
            "рейс",
            "самолет",
            "перрон",
            "путевка",
            "рейсовый",
        }
        self.mode_keywords = {
            TransportMode.METRO: {"метро", "метрополитен", "мцк", "мцд", "подземк"},
            TransportMode.BUS: {"автобус", "маршрутк", "пазик", "шаттл"},
            TransportMode.TRAM: {"трамвай", "трам", "троллейб"},
            TransportMode.TRAIN: {"поезд", "жд", "электричк", "ласточк", "сапсан"},
            TransportMode.AIRPLANE: {"самолет", "аэропорт", "борд", "рейс"},
            TransportMode.WATER: {"паром", "теплоход", "судно", "лодк"},
            TransportMode.TAXI: {"такси", "яндекс", "uber", "болт", "делимобил"},
        }
        self.positive_lexeme = {"спасибо", "классно", "отлично", "люблю"}
        self.negative_lexeme = {"ужас", "задержка", "наплевать", "негатив", "скандал"}

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
        adjusted = probs.copy()
        if tokens & self.negative_lexeme:
            adjusted[0] += 0.2
            adjusted[2] -= 0.1
        if tokens & self.positive_lexeme:
            adjusted[2] += 0.2
            adjusted[0] -= 0.1
        adjusted = np.clip(adjusted, 0.01, 0.98)
        return adjusted / np.sum(adjusted)

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

