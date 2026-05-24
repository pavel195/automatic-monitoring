from django.conf import settings


def test_channel_polling_runs_every_second_by_default():
    assert settings.CELERY_BEAT_SCHEDULE["poll_telegram"]["schedule"] == 1.0
    assert settings.CELERY_BEAT_SCHEDULE["poll_vk"]["schedule"] == 1.0


def test_external_channel_polling_uses_short_waits_by_default():
    assert settings.TELEGRAM_LONG_POLL_TIMEOUT == 0
    assert settings.VK_LONG_POLL_WAIT_SECONDS == 1
