from routing.nlp_classifier import KeywordClassifier


def test_classifier_detects_priority_and_category():
    classifier = KeywordClassifier()
    result = classifier.predict("На маршруте 12 пожар и дым в салоне")
    assert result.category == "incident"
    assert result.priority == 4
    assert result.group == "safety"

