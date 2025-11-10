from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional
from enum import Enum
import uuid
from rq import Queue
from rq.job import Job
from redis import Redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "langflow.queue")

redis_conn = Redis.from_url(REDIS_URL)
task_queue = Queue(QUEUE_NAME, connection=redis_conn)

app = FastAPI(title="Langflow Queue API")


class TaskRequest(BaseModel):
    flow_id: str
    input_value: Optional[str] = None
    input_type: Optional[str] = "text"
    tweaks: Optional[dict] = None
    session_id: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class EventDeliveryType(str, Enum):
    STREAMING = "streaming"
    DIRECT = "direct"
    POLLING = "polling"


class InputValueRequest(BaseModel):
    components: Optional[list[str]] = []
    input_value: Optional[str] = None
    session: Optional[str] = None
    type: Optional[str] = "any"


class FlowDataRequest(BaseModel):
    nodes: list[dict]
    edges: list[dict]
    viewport: Optional[dict] = None


class BuildFlowResponse(BaseModel):
    status: str
    message: str
    flow_id: str


@app.post("/tasks", response_model=TaskResponse)
def create_task(req: TaskRequest):
    task_id = str(uuid.uuid4())
    payload = {
        "input_value": req.input_value,
        "input_type": req.input_type,
        "tweaks": req.tweaks,
        "session_id": req.session_id,
    }

    from worker.tasks import process_langflow_task  # implemented in services/worker

    job = task_queue.enqueue(
        process_langflow_task,
        task_id,
        req.flow_id,
        payload,
        job_id=task_id,
        result_ttl=3600,
        failure_ttl=86400,
    )

    return TaskResponse(task_id=task_id, status="pending", message=f"enqueued: {job.id}")


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    # Fetch job by id independent of queue
    job = Job.fetch(task_id, connection=redis_conn)
    if not job:
        raise HTTPException(status_code=404, detail="Task not found")

    if job.is_finished:
        return {"task_id": task_id, "status": "completed", "result": job.result}
    if job.is_failed:
        return {"task_id": task_id, "status": "failed", "error": str(job.exc_info)}

    return {"task_id": task_id, "status": job.get_status() or "unknown"}


@app.post("/api/v1/build/{flow_id}/flow")
def build_flow(
    flow_id: str,
    inputs: Optional[InputValueRequest] = Body(None, embed=True),
    data: Optional[FlowDataRequest] = Body(None, embed=True),
    files: Optional[list[str]] = Query(None),
    stop_component_id: Optional[str] = Query(None),
    start_component_id: Optional[str] = Query(None),
    log_builds: bool = Query(True),
    flow_name: Optional[str] = Query(None),
    event_delivery: EventDeliveryType = Query(EventDeliveryType.POLLING),
):
    """Build and process a flow endpoint (placeholder implementation).
    
    This endpoint accepts the same parameters as the Langflow build endpoint
    but currently just returns OK. Implementation will be added later.
    """
    return BuildFlowResponse(
        status="ok",
        message="Endpoint received data successfully",
        flow_id=flow_id
    )


@app.get("/api/v1/build/{job_id}/events")
def get_build_events(
    job_id: str,
    event_delivery: EventDeliveryType = Query(EventDeliveryType.STREAMING),
):
    """Retrieve build events (stub implementation)."""
    return {
        "job_id": job_id,
        "event_delivery": event_delivery.value,
        "status": "pending",
        "message": "Events retrieval not implemented yet",
    }


@app.get("/health")
def health():
    try:
        redis_conn.ping()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

