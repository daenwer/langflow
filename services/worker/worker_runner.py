#!/usr/bin/env python3
"""Runner script for RQ worker for debugging purposes."""
import os
from rq import Worker, Queue, Connection
from redis import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "langflow.queue")

redis_conn = Redis.from_url(REDIS_URL)
queue = Queue(QUEUE_NAME, connection=redis_conn)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker([queue])
        worker.work()

