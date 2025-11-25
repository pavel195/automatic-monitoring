from routing.ai.transport_intent import TransportIntentModel
from tickets.models import Sentiment


def test_transport_intent_model_detects_transport_and_sentiment():
    model = TransportIntentModel()
    text = "Поезд на Ленинград опаздывает, пассажиры возмущены"
    prediction = model.predict(text)
    assert prediction.is_transport is True
    assert prediction.sentiment in {
        Sentiment.NEGATIVE,
        Sentiment.NEUTRAL,
        Sentiment.POSITIVE,
    }


def test_transport_intent_model_filters_non_transport():
    model = TransportIntentModel()
    text = "Вкусная пицца и хороший бариста"
    prediction = model.predict(text)
    assert prediction.is_transport is False
    assert isinstance(prediction.transport_score, float)

