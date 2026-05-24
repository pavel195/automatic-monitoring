import logging

import requests

from ingestion.connectors.telegram_client import TelegramConnector


class TelegramResponse:
    def __init__(self, payload):
        self.payload = payload
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        self.store[key] = value

    def delete(self, key):
        self.store.pop(key, None)


def test_telegram_connector_reads_chat_ids_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MONITOR_CHAT_ID", "100, 200")
    monkeypatch.setenv("TELEGRAM_DISCUSSION_CHAT_IDS", "300")
    monkeypatch.setattr(TelegramConnector, "_init_state_store", lambda self: None)

    connector = TelegramConnector(bot_token="token")

    assert connector.chat_ids == {"100", "200"}
    assert connector.discussion_chat_ids == {"300"}


def test_telegram_connector_extracts_compact_attachments():
    message = {
        "photo": [
            {"file_id": "small", "width": 100, "height": 100},
            {"file_id": "large", "width": 1000, "height": 1000},
        ],
        "document": {"file_id": "doc-id", "file_name": "claim.pdf"},
        "voice": {"file_id": "voice-id"},
    }

    assert TelegramConnector._extract_attachments(message) == [
        {"type": "photo", "file_id": "large"},
        {"type": "document", "file_id": "doc-id", "file_name": "claim.pdf"},
        {"type": "voice", "file_id": "voice-id"},
    ]


def test_telegram_connector_uses_zero_offset_when_redis_unavailable(monkeypatch):
    class BrokenRedis:
        def get(self, key):
            raise ConnectionError("redis is down")

    monkeypatch.setattr(
        TelegramConnector,
        "_init_state_store",
        lambda self: setattr(self, "redis", BrokenRedis()),
    )

    connector = TelegramConnector(bot_token="token")

    assert connector._offset == 0


def test_telegram_connector_redacts_token_from_request_errors(monkeypatch, caplog):
    token = "123456:test-secret-token"
    monkeypatch.setattr(TelegramConnector, "_init_state_store", lambda self: None)

    def raise_connection_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError(
            f"https://api.telegram.org/bot{token}/getUpdates is unreachable"
        )

    monkeypatch.setattr(requests, "get", raise_connection_error)

    connector = TelegramConnector(bot_token=token)
    with caplog.at_level(logging.WARNING):
        assert connector.poll() == []

    assert token not in caplog.text
    assert "[redacted]" in caplog.text


def test_telegram_connector_uses_configured_poll_timeout(monkeypatch, settings):
    settings.TELEGRAM_LONG_POLL_TIMEOUT = 0
    settings.TELEGRAM_CONNECT_TIMEOUT = 1.0
    settings.TELEGRAM_READ_TIMEOUT = 1.0
    monkeypatch.setattr(TelegramConnector, "_init_state_store", lambda self: None)

    def get_updates(*args, **kwargs):
        assert kwargs["params"]["timeout"] == 0
        assert kwargs["timeout"] == (1.0, 1.0)
        return TelegramResponse({"ok": True, "result": []})

    monkeypatch.setattr(requests, "get", get_updates)

    connector = TelegramConnector(bot_token="token")

    assert connector.poll() == []


def test_telegram_connector_persists_offset_when_quick_action_reply_times_out(
    monkeypatch, caplog
):
    redis = FakeRedis()
    monkeypatch.setattr(
        TelegramConnector,
        "_init_state_store",
        lambda self: setattr(self, "redis", redis),
    )

    def get_updates(*args, **kwargs):
        assert kwargs["timeout"] == TelegramConnector._request_timeout()
        return TelegramResponse(
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 42,
                        "message": {
                            "message_id": 7,
                            "chat": {"id": 111, "type": "private"},
                            "from": {"username": "passenger"},
                            "text": "Жалоба",
                        },
                    }
                ],
            }
        )

    def send_message(*args, **kwargs):
        assert kwargs["timeout"] == TelegramConnector._request_timeout()
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(requests, "get", get_updates)
    monkeypatch.setattr(requests, "post", send_message)

    connector = TelegramConnector(bot_token="token", allow_private=True)

    with caplog.at_level(logging.WARNING):
        assert connector.poll() == []

    assert redis.store[connector.offset_key] == 43
    assert redis.store[connector._private_action_key("111")] == "Жалоба"
    assert "Не удалось отправить ответ Telegram" in caplog.text


def test_telegram_connector_acknowledges_private_message(monkeypatch):
    redis = FakeRedis()
    sent_messages = []
    monkeypatch.setattr(
        TelegramConnector,
        "_init_state_store",
        lambda self: setattr(self, "redis", redis),
    )

    def get_updates(*args, **kwargs):
        return TelegramResponse(
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 51,
                        "message": {
                            "message_id": 9,
                            "chat": {"id": 222, "type": "private"},
                            "from": {"username": "passenger"},
                            "text": "Поезд задерживается",
                        },
                    }
                ],
            }
        )

    def send_message(*args, **kwargs):
        sent_messages.append(kwargs["json"])
        return TelegramResponse({"ok": True, "result": {"message_id": 10}})

    monkeypatch.setattr(requests, "get", get_updates)
    monkeypatch.setattr(requests, "post", send_message)

    connector = TelegramConnector(bot_token="token", allow_private=True)

    events = connector.poll()

    assert len(events) == 1
    assert events[0]["payload"] == "Поезд задерживается"
    assert sent_messages == [
        {
            "chat_id": "222",
            "text": "✅ Обращение принято. Оператор увидит его в системе в ближайшие секунды.",
            "disable_web_page_preview": True,
        }
    ]
    assert redis.store[connector.offset_key] == 52
