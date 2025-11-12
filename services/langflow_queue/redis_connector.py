from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from redis import Redis

from .base import BaseQueueConnector


class RedisQueueConnector(BaseQueueConnector):
    """Коннектор очереди на основе хранилища Redis."""

    def __init__(
        self,
        *,
        redis_conn: Redis,
        queue_name: str = "langflow.queue",
        task_key_prefix: str = "task",
        ttl_seconds: int = 60 * 60 * 24,
    ) -> None:
        self.redis = redis_conn
        self.queue_name = queue_name
        self.task_key_prefix = task_key_prefix.rstrip(":")
        self.ttl_seconds = ttl_seconds

    def _key(self, task_id: str) -> str:
        return f"{self.task_key_prefix}:{task_id}"

    def _store(self, task_record: dict) -> None:
        task_id = task_record["task_id"]
        self.redis.setex(
            self._key(task_id),
            self.ttl_seconds,
            json.dumps(task_record, ensure_ascii=False),
        )

    def _load(self, task_id: str) -> Optional[dict]:
        raw = self.redis.get(self._key(task_id))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _scan_keys(self) -> Iterable[str]:
        pattern = f"{self.task_key_prefix}:*"
        return self.redis.scan_iter(match=pattern)

    def enqueue(self, task_record: dict) -> str:
        """Сохраняет запись задачи в Redis и добавляет в очередь."""
        task_id = task_record["task_id"]
        self._store(task_record)
        self.redis.lpush(self.queue_name, task_id)
        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._load(task_id)

    def list_tasks(self) -> list[dict]:
        records: list[dict] = []
        for key in self._scan_keys():
            raw = self.redis.get(key)
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return records

    def update_task(self, task_id: str, updates: dict) -> None:
        existing = self._load(task_id)
        if not existing:
            return
        existing.update(updates)
        self._store(existing)

    def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """Извлекает задачу из очереди. Возвращает None, если очередь пуста.
        
        Args:
            timeout: Таймаут блокировки в секундах. 0 означает неблокирующий режим.
                    Если > 0, использует BLPOP (блокирующее извлечение).
        """
        if timeout > 0:
            result = self.redis.blpop(self.queue_name, timeout=timeout)
            if result is None:
                return None
            task_id = result[1].decode() if isinstance(result[1], bytes) else result[1]
        else:
            task_id = self.redis.rpop(self.queue_name)
            if task_id is None:
                return None
            if isinstance(task_id, bytes):
                task_id = task_id.decode()
        
        # Получаем полную запись задачи по task_id
        return self._load(task_id)

    def ping(self) -> None:
        """Проверяет подключение к Redis."""
        self.redis.ping()


def create_redis_queue_connector(
    redis_conn: Redis,
    *,
    queue_name: str = "langflow.queue",
    task_key_prefix: str = "task",
    ttl_seconds: int = 60 * 60 * 24,
) -> RedisQueueConnector:
    return RedisQueueConnector(
        redis_conn=redis_conn,
        queue_name=queue_name,
        task_key_prefix=task_key_prefix,
        ttl_seconds=ttl_seconds,
    )


__all__ = ["RedisQueueConnector", "create_redis_queue_connector"]

