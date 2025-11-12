from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class BaseQueueConnector(Protocol):
    """Общий интерфейс для бэкендов очередей."""

    def enqueue(self, task_record: dict) -> str:
        """Сохраняет и ставит задачу в очередь. Возвращает сгенерированный task_id."""
        ...

    def get_task(self, task_id: str) -> Optional[dict]:
        """Получает ранее сохранённую запись задачи."""
        ...

    def list_tasks(self) -> list[dict]:
        """Возвращает все известные записи задач."""
        ...

    def update_task(self, task_id: str, updates: dict) -> None:
        """Применяет обновления (статус, результат, ошибка и т.д.) к записи задачи."""
        ...

    def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """Извлекает задачу из очереди. Возвращает None, если очередь пуста.
        
        Args:
            timeout: Таймаут блокировки в секундах. 0 означает неблокирующий режим.
        """
        ...

    def ping(self) -> None:
        """Проверяет подключение к базовому бэкенду очереди."""
        ...


__all__ = ["BaseQueueConnector"]

