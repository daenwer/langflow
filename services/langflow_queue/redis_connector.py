from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from redis import Redis

from .base import BaseQueueConnector


class RedisQueueConnector(BaseQueueConnector):
    """Queue connector backed by Redis storage."""

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
        """Persist the task record in Redis and add to queue."""
        task_id = task_record["task_id"]
        # Store task record
        self._store(task_record)
        # Add task_id to queue (LPUSH - add to left/head of list)
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
        """Dequeue a task from the queue. Returns None if queue is empty.
        
        Args:
            timeout: Blocking timeout in seconds. 0 means non-blocking.
                    If > 0, uses BLPOP (blocking pop).
        """
        if timeout > 0:
            # Blocking pop - waits for task to appear
            result = self.redis.blpop(self.queue_name, timeout=timeout)
            if result is None:
                return None
            # result is (queue_name, task_id)
            task_id = result[1].decode() if isinstance(result[1], bytes) else result[1]
        else:
            # Non-blocking pop
            task_id = self.redis.rpop(self.queue_name)
            if task_id is None:
                return None
            if isinstance(task_id, bytes):
                task_id = task_id.decode()
        
        # Get full task record by task_id
        return self._load(task_id)

    def ping(self) -> None:
        """Check Redis connectivity."""
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

