from ingestion.connectors.telegram_client import TelegramConnector


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
