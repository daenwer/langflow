from __future__ import annotations

import os

from redis import Redis

from .base import BaseQueueConnector
from .redis_connector import create_redis_queue_connector, RedisQueueConnector


def init_queue_connector() -> BaseQueueConnector:
    """Инициализирует коннектор очереди."""
    return init_redis_queue_connector()


def init_redis_queue_connector() -> RedisQueueConnector:
    """Создаёт коннектор очереди на основе Redis."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    queue_name = os.getenv("QUEUE_NAME", "langflow.queue")
    task_key_prefix = os.getenv("TASK_KEY_PREFIX", "task")
    ttl_seconds = int(os.getenv("TASK_TTL_SECONDS", "86400"))

    redis_conn = Redis.from_url(redis_url)
    return create_redis_queue_connector(
        redis_conn=redis_conn,
        queue_name=queue_name,
        task_key_prefix=task_key_prefix,
        ttl_seconds=ttl_seconds,
    )

__all__ = ["init_queue_connector", "init_redis_queue_connector"]
