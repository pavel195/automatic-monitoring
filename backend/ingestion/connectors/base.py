from abc import ABC, abstractmethod
from typing import Iterable, Mapping


class BaseConnector(ABC):
    """Базовый интерфейс для коннекторов входящих каналов."""

    @abstractmethod
    def poll(self) -> Iterable[Mapping]:
        """Собирает новые сообщения и возвращает события в виде dict."""

    @abstractmethod
    def acknowledge(self, message_id: str) -> None:
        """Помечает сообщение как обработанное на стороне источника."""

