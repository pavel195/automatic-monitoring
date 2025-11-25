import re
from dataclasses import dataclass
from typing import Dict


@dataclass
class ClassificationResult:
    category: str
    priority: int
    group: str
    title: str


class KeywordClassifier:
    """Простейший baseline на ключевых словах.

    В бою сюда можно подключить fastText/BERT, но для MVP даём
    воспроизводимый результат без сложного инференса.
    """

    CATEGORY_KEYWORDS: Dict[str, tuple[str, ...]] = {
        "complaint": ("жалоб", "недоволен", "не работает", "опоздан", "драка"),
        "praise": ("спасибо", "благодарю", "отлично"),
        "request": ("когда", "расписан", "где", "подскаж"),
        "incident": ("авари", "угроза", "безопасн", "пожар"),
    }

    PRIORITY_KEYWORDS: Dict[int, tuple[str, ...]] = {
        4: ("пожар", "авари", "угроза", "травм"),
        3: ("слом", "не работает", "опазд", "задерж", "пробк", "наруш"),
        2: ("жалу", "неудоб", "не хватает"),
        1: ("спасибо", "предлож"),
    }

    GROUP_KEYWORDS: Dict[str, tuple[str, ...]] = {
        "operations": ("водител", "маршрут", "рейс"),
        "safety": ("пожар", "угроза", "драка", "безопас"),
        "service": ("касс", "приложен", "оплат"),
    }

    def predict(self, text: str) -> ClassificationResult:
        lower = text.lower()
        category = self._match_by_dict(
            lower, self.CATEGORY_KEYWORDS, default="request"
        )
        priority = self._match_priority(lower)
        group = self._match_by_dict(lower, self.GROUP_KEYWORDS, default="operations")
        title = self._extract_title(lower)
        return ClassificationResult(
            category=category,
            priority=priority,
            group=group,
            title=title,
        )

    def _match_priority(self, text: str) -> int:
        for priority, keywords in sorted(
            self.PRIORITY_KEYWORDS.items(), reverse=True
        ):
            if any(keyword in text for keyword in keywords):
                return priority
        return 2

    @staticmethod
    def _match_by_dict(text: str, mapping: Dict, default: str) -> str:
        for label, keywords in mapping.items():
            if any(keyword in text for keyword in keywords):
                return label
        return default

    @staticmethod
    def _extract_title(text: str) -> str:
        sentences = re.split(r"[.!?]", text)
        clean = sentences[0].strip()
        return clean[:120] or "Сообщение пассажира"

