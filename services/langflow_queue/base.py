from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class BaseQueueConnector(Protocol):
    """Common interface for queue backends."""

    def enqueue(self, task_record: dict) -> str:
        """Persist and enqueue a task. Returns the generated task_id."""
        ...

    def get_task(self, task_id: str) -> Optional[dict]:
        """Retrieve a previously stored task record."""
        ...

    def list_tasks(self) -> list[dict]:
        """Return all known task records."""
        ...

    def update_task(self, task_id: str, updates: dict) -> None:
        """Apply updates (status, result, error, etc.) to the task record."""
        ...

    def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """Dequeue a task from the queue. Returns None if queue is empty.
        
        Args:
            timeout: Blocking timeout in seconds. 0 means non-blocking.
        """
        ...

    def ping(self) -> None:
        """Check connectivity with the underlying queue backend."""
        ...


__all__ = ["BaseQueueConnector"]

