"""Тесты для улучшенного классификатора."""

from routing.nlp_classifier import KeywordClassifier


def test_classifier_detects_new_categories():
    """Тест определения новых категорий."""
    classifier = KeywordClassifier()
    
    # Тест категории "Предложение"
    result = classifier.predict("Предлагаю добавить новые маршруты")
    assert result.category == "suggestion"
    
    # Тест категории "Вопрос по оплате"
    result = classifier.predict("Как оплатить проездной билет?")
    assert result.category == "payment"


def test_classifier_improved_priority():
    """Тест улучшенной логики приоритетов."""
    classifier = KeywordClassifier()
    
    # Инцидент должен быть критическим
    result = classifier.predict("Пожар в вагоне метро")
    assert result.priority == 4
    assert result.category == "incident"
    
    # Множественные критические маркеры
    result = classifier.predict("Пожар и взрыв в автобусе, нужна скорая")
    assert result.priority == 4
    
    # Жалоба должна быть минимум средней
    result = classifier.predict("Жалуюсь на плохое обслуживание")
    assert result.priority >= 2
    
    # Благодарность должна быть низкой
    result = classifier.predict("Спасибо за отличную работу")
    assert result.priority <= 1


def test_classifier_extended_keywords():
    """Тест расширенных ключевых слов."""
    classifier = KeywordClassifier()
    
    # Новые синонимы для жалоб
    result = classifier.predict("Возмущен качеством обслуживания")
    assert result.category == "complaint"
    
    result = classifier.predict("Разочарован работой транспорта")
    assert result.category == "complaint"
    
    # Новые синонимы для благодарности
    result = classifier.predict("Восхищен сервисом")
    assert result.category == "praise"
    
    result = classifier.predict("Рекомендую всем")
    assert result.category == "praise"


def test_classifier_group_detection():
    """Тест определения групп."""
    classifier = KeywordClassifier()
    
    # Группа maintenance
    result = classifier.predict("Сломался автобус, нужен ремонт")
    assert result.group == "maintenance"
    
    # Группа operations
    result = classifier.predict("Водитель опоздал на маршрут")
    assert result.group == "operations"

