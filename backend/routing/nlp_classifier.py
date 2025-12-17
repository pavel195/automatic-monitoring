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
        "complaint": (
            "жалоб", "недоволен", "не работает", "опоздан", "драка",
            "плохо", "ужасно", "кошмар", "неприятно", "разочарован",
            "некачественно", "неудобно", "проблем", "сломал", "поломк",
            "неприемлемо", "возмущен", "недовольств", "не устраивает",
            "некачественн", "неудовлетворительно", "неприятност",
        ),
        "praise": (
            "спасибо", "благодарю", "отлично", "замечательно", "прекрасно",
            "великолепно", "супер", "класс", "молодцы", "хорошо",
            "отличн", "восхищен", "доволен", "нравится", "люблю",
            "рекомендую", "похвальн", "благодарност", "признателен",
        ),
        "request": (
            "когда", "расписан", "где", "подскаж", "интерес", "вопрос",
            "уточн", "узнать", "информац", "как", "сколько", "можно",
            "возможно", "нужно", "требуется", "хочу", "хотел бы",
            "прошу", "помогите", "помощь", "консультац", "справк",
        ),
        "incident": (
            "авари", "угроза", "безопасн", "пожар", "травм", "ранен",
            "столкновен", "дтп", "происшеств", "инцидент", "чрезвычайн",
            "экстренн", "критическ", "опасн", "угроз", "риск",
        ),
        "suggestion": (
            "предложен", "идея", "рекомендац", "совет", "можно было бы",
            "хотелось бы", "желательно", "лучше", "улучшен", "оптимизац",
            "предлагаю", "предлага", "добавить", "новые", "новый",
        ),
        "payment": (
            "оплат", "платеж", "деньг", "стоимость", "цена", "тариф",
            "билет", "проездн", "проездной", "возврат", "компенсац", "средств",
            "карт", "наличн", "безналичн", "касс", "терминал", "оплатить",
        ),
    }

    PRIORITY_KEYWORDS: Dict[int, tuple[str, ...]] = {
        4: (
            "пожар", "авари", "угроза", "травм", "ранен", "кров",
            "взрыв", "террор", "заложник", "захват", "насил",
            "экстренн", "скорая", "полиц", "мчс", "эвакуац",
            "критическ", "смерт", "опасн", "угроз", "риск",
        ),
        3: (
            "слом", "не работает", "опазд", "задерж", "пробк", "наруш",
            "поломк", "неисправн", "отмен", "отменен", "отменя",
            "не пришел", "не приехал", "не пришл", "не приехал",
            "проблем", "сбой", "ошибк", "недоступн", "недоступен",
            "переполнен", "переполн", "давк", "толп", "скандал",
        ),
        2: (
            "жалу", "неудоб", "не хватает", "неудобств", "некомфортн",
            "неприятн", "некачественн", "недоволен", "не устраивает",
            "плохо", "ужасно", "неприемлемо", "неприятност",
        ),
        1: (
            "спасибо", "предлож", "идея", "рекомендац", "совет",
            "благодар", "отлично", "хорошо", "нравится",
        ),
    }

    GROUP_KEYWORDS: Dict[str, tuple[str, ...]] = {
        "maintenance": (
            "ремонт", "техническ", "обслуживан", "техобслуж",
            "поломк", "неисправн", "слом", "сломал", "слома", "не работает", "сбой",
            "техник", "оборудован", "инфраструктур", "состоян",
        ),
        "safety": (
            "пожар", "угроза", "драка", "безопас", "травм", "ранен",
            "авари", "дтп", "столкновен", "происшеств", "инцидент",
            "насил", "угроз", "риск", "опасн", "экстренн",
        ),
        "service": (
            "касс", "приложен", "оплат", "билет", "проездн", "тариф",
            "цена", "стоимость", "платеж", "возврат", "компенсац",
            "обслуж", "персонал", "сотрудник", "консультац", "справк",
            "информац", "помощь", "поддержк", "клиентск",
        ),
        "operations": (
            "водител", "маршрут", "рейс", "расписан", "график",
            "движен", "движени", "транспорт", "автобус", "поезд",
            "метро", "трамвай", "рейсов", "маршрутн", "остановк",
            "станц", "вокзал", "перрон", "платформ", "поездк",
        ),
    }

    def predict(self, text: str) -> ClassificationResult:
        lower = text.lower()
        # Сначала проверяем более специфичные категории (payment, suggestion)
        # чтобы они имели приоритет над общими (request)
        category = "request"  # По умолчанию
        # Проверяем категории в порядке специфичности
        for cat in ["payment", "suggestion", "incident", "complaint", "praise", "request"]:
            if cat in self.CATEGORY_KEYWORDS:
                if any(keyword in lower for keyword in self.CATEGORY_KEYWORDS[cat]):
                    category = cat
                    break
        
        priority = self._match_priority(lower, category)
        group = self._match_by_dict(lower, self.GROUP_KEYWORDS, default="operations")
        title = self._extract_title(lower)
        return ClassificationResult(
            category=category,
            priority=priority,
            group=group,
            title=title,
        )

    def _match_priority(self, text: str, category: str) -> int:
        """Определение приоритета с учетом категории и ключевых слов."""
        # Базовый приоритет из ключевых слов
        base_priority = 2  # Средний по умолчанию
        for priority, keywords in sorted(
            self.PRIORITY_KEYWORDS.items(), reverse=True
        ):
            if any(keyword in text for keyword in keywords):
                base_priority = priority
                break
        
        # Корректировка на основе категории
        if category == "incident":
            base_priority = max(base_priority, 4)  # Инциденты всегда критичны
        elif category == "complaint":
            base_priority = max(base_priority, 2)  # Жалобы минимум средние
        elif category == "praise":
            base_priority = min(base_priority, 1)  # Благодарности низкий приоритет
        elif category == "suggestion":
            base_priority = min(base_priority, 1)  # Предложения низкий приоритет
        
        # Повышение приоритета при множественных ключевых словах
        critical_count = sum(1 for kw in self.PRIORITY_KEYWORDS[4] if kw in text)
        high_count = sum(1 for kw in self.PRIORITY_KEYWORDS[3] if kw in text)
        
        if critical_count >= 2:
            base_priority = 4
        elif critical_count >= 1 and high_count >= 1:
            base_priority = max(base_priority, 4)
        elif high_count >= 2:
            base_priority = max(base_priority, 3)
        
        return base_priority

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

