#!/usr/bin/env python3
"""Worker that dequeues tasks from Redis queue and processes them."""
import os
import httpx
from datetime import datetime, timezone
from langflow_queue.factory import init_queue_connector


def process_task(task_record: dict, queue_connector) -> dict:
    """Process a task by making HTTP request to Langflow API.
    
    Returns:
        dict: Response data to be stored in task_record["response"]
    """
    request = task_record.get("request", {})
    method = request.get("method", "POST").upper()
    endpoint = request.get("endpoint", "")
    payload = request.get("payload", {})
    task_id = task_record.get("task_id")
    
    # Get Langflow URL from environment
    langflow_url = os.getenv("LANGFLOW_URL", "http://langflow:7860")
    langflow_url = langflow_url.rstrip("/")
    
    # Build full URL
    full_url = f"{langflow_url}{endpoint}"
    
    print(f"Processing task {task_id}")
    print(f"Method: {method}")
    print(f"URL: {full_url}")
    print(f"Payload: {payload}")
    
    try:
        with httpx.Client(timeout=300.0) as client:
            match method:
                case "POST":
                    # POST request - send body as JSON, query_params as query parameters
                    body_data = payload.get("body", {})
                    query_params = payload.get("query_params", {})
                    response = client.post(
                        full_url,
                        json=body_data,
                        params=query_params,
                    )
                case "GET":
                    # GET request - send query_params as query parameters
                    query_params = payload.get("query_params", payload)
                    response = client.get(
                        full_url,
                        params=query_params,
                    )
                case _:
                    return {"error": f"Unsupported HTTP method: {method}"}
            
            response.raise_for_status()
            
            # Parse response
            try:
                response_data = response.json()
            except Exception:
                # If not JSON, return text
                response_data = {"text": response.text}
            
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response_data}")
            
            return {
                "status_code": response.status_code,
                "data": response_data,
            }
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"HTTP error: {error_msg}")
        return {
            "status_code": e.response.status_code,
            "error": error_msg,
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error making request: {error_msg}")
        return {
            "error": error_msg,
        }


def main():
    """Main worker loop that dequeues tasks from queue."""
    queue_connector = init_queue_connector()
    dequeue_timeout = int(os.getenv("WORKER_DEQUEUE_TIMEOUT", "5"))
    
    print("Worker started, waiting for tasks from queue...")
    
    while True:
        try:
            # Blocking dequeue - waits for new task to appear in queue
            task_record = queue_connector.dequeue(timeout=dequeue_timeout)
            
            if task_record is None:
                # Timeout - no tasks in queue, continue waiting
                continue
            
            task_id = task_record.get("task_id")
            print(f"Processing task: {task_id}")
            
            try:
                # Mark as processing
                queue_connector.update_task(task_id, {"status": "processing"})
                
                # Process the task
                response_data = process_task(task_record, queue_connector)
                
                # Update task with response
                queue_connector.update_task(task_id, {
                    "status": "completed",
                    "response": {
                        "data": response_data,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                })
                print(f"Task {task_id} completed successfully")
                
            except Exception as e:
                print(f"Error processing task {task_id}: {e}")
                queue_connector.update_task(task_id, {
                    "status": "failed",
                    "error": str(e),
                    "response": {
                        "error": str(e),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                })
                
        except KeyboardInterrupt:
            print("Worker stopped")
            break
        except Exception as e:
            print(f"Error in worker loop: {e}")
            continue


if __name__ == "__main__":
    main()

