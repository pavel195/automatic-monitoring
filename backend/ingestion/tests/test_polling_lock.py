from ingestion.tasks import polling_lock


class FakeRedisClient:
    def __init__(self, acquired=True):
        self.acquired = acquired
        self.store = {}
        self.deleted = []

    def set(self, key, value, nx=False, ex=None):
        if not self.acquired:
            return False
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.deleted.append(key)
        self.store.pop(key, None)


def test_polling_lock_skips_when_previous_run_is_active(monkeypatch):
    client = FakeRedisClient(acquired=False)
    monkeypatch.setattr(
        "ingestion.tasks.redis.Redis.from_url",
        lambda *args, **kwargs: client,
    )

    with polling_lock("telegram", ttl=10) as acquired:
        assert acquired is False


def test_polling_lock_releases_owned_lock(monkeypatch):
    client = FakeRedisClient(acquired=True)
    monkeypatch.setattr(
        "ingestion.tasks.redis.Redis.from_url",
        lambda *args, **kwargs: client,
    )

    with polling_lock("telegram", ttl=10) as acquired:
        assert acquired is True
        assert "ingestion:poll_lock:telegram" in client.store

    assert client.deleted == ["ingestion:poll_lock:telegram"]
