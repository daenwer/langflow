#!/usr/bin/env python3
"""Воркер, который извлекает задачи из очереди Redis и обрабатывает их."""
import os
import logging
import httpx
from datetime import datetime, timezone
from langflow_queue.factory import init_queue_connector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def process_task(task_record: dict, queue_connector) -> dict:
    """Обрабатывает задачу, выполняя HTTP запрос к API Langflow"""
    request = task_record.get("request", {})
    method = request.get("method", "POST").upper()
    endpoint = request.get("endpoint", "")
    payload = request.get("payload", {})
    task_id = task_record.get("task_id")
    
    langflow_url = os.getenv("LANGFLOW_URL", "http://langflow:7860")
    langflow_url = langflow_url.rstrip("/")
    
    full_url = f"{langflow_url}{endpoint}"
    
    logger.info(f"Processing task {task_id}", extra={"task_id": task_id})
    logger.debug(f"Request details: method={method}, url={full_url}, payload={payload}", extra={"task_id": task_id})
    
    try:
        with httpx.Client(timeout=300.0) as client:
            match method:
                case "POST":
                    body_data = payload.get("body", {})
                    query_params = payload.get("query_params", {})
                    response = client.post(
                        full_url,
                        json=body_data,
                        params=query_params,
                    )
                case "GET":
                    query_params = payload.get("query_params", payload)
                    response = client.get(
                        full_url,
                        params=query_params,
                    )
                case _:
                    return {"error": f"Unsupported HTTP method: {method}"}
            
            response.raise_for_status()
            
            try:
                response_data = response.json()
            except Exception:
                response_data = {"text": response.text}
            
            logger.info(
                f"Task {task_id} completed: status={response.status_code}",
                extra={"task_id": task_id, "status_code": response.status_code}
            )
            logger.debug(f"Response data: {response_data}", extra={"task_id": task_id})
            
            return {
                "status_code": response.status_code,
                "data": response_data,
            }
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        logger.error(
            f"HTTP error for task {task_id}: {error_msg}",
            extra={"task_id": task_id, "status_code": e.response.status_code},
            exc_info=True
        )
        return {
            "status_code": e.response.status_code,
            "error": error_msg,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error making request for task {task_id}: {error_msg}",
            extra={"task_id": task_id},
            exc_info=True
        )
        return {
            "error": error_msg,
        }


def main():
    """Основной цикл воркера, который извлекает задачи из очереди."""
    queue_connector = init_queue_connector()
    dequeue_timeout = int(os.getenv("WORKER_DEQUEUE_TIMEOUT", "5"))
    
    logger.info("Worker started, waiting for tasks from queue...")
    
    while True:
        try:
            task_record = queue_connector.dequeue(timeout=dequeue_timeout)
            
            if task_record is None:
                logger.debug("No tasks in queue, continuing to wait...")
                continue
            
            task_id = task_record.get("task_id")
            logger.info(f"Dequeued task: {task_id}", extra={"task_id": task_id})
            
            try:
                queue_connector.update_task(task_id, {"status": "processing"})
                
                response_data = process_task(task_record, queue_connector)
                
                queue_connector.update_task(task_id, {
                    "status": "completed",
                    "response": {
                        "data": response_data,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                })
                logger.info(f"Task {task_id} completed successfully", extra={"task_id": task_id})
                
            except Exception as e:
                logger.error(
                    f"Error processing task {task_id}: {e}",
                    extra={"task_id": task_id},
                    exc_info=True
                )
                queue_connector.update_task(task_id, {
                    "status": "failed",
                    "error": str(e),
                    "response": {
                        "error": str(e),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                })
                
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            continue


if __name__ == "__main__":
    main()
