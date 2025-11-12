from fastapi import FastAPI, HTTPException, Body, Query, Request
import json
from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum

from langflow_queue.factory import init_queue_connector
from .task_utils import build_task_record


queue_connector = init_queue_connector()

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
    # STREAMING = "streaming"
    # DIRECT = "direct"
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


def _parse_response_events(response: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"status_code": None, "events": [], "raw_text": None}

    status_code = response.get("data", {}).get("status_code")
    text = (
        response.get("data", {})
        .get("data", {})
        .get("text")
        if isinstance(response.get("data"), dict)
        else None
    )

    events: list[Any] = []
    if isinstance(text, str):
        for chunk in text.split("\n\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                events.append(json.loads(chunk))
            except json.JSONDecodeError:
                events.append({"raw": chunk})

    return {"status_code": status_code, "events": events, "raw_text": text}


@app.get("/get_tasks", tags=["internal"])
def get_tasks():
    """Return all known task records from the queue backend."""
    tasks = queue_connector.list_tasks()
    return {"tasks": tasks, "count": len(tasks)}


@app.get("/get_task/{task_id}", tags=["internal"])
def get_task(task_id: str):
    task_record = queue_connector.get_task(task_id)
    if not task_record:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_record


@app.post("/api/v1/build/{flow_id}/flow", tags=["langflow"])
async def build_flow(
    flow_id: str,
    request: Request,
    inputs: Optional[InputValueRequest] = Body(None, embed=True),
    data: Optional[FlowDataRequest] = Body(None, embed=True),
    files: Optional[list[str]] = Query(None),
    stop_component_id: Optional[str] = Query(None),
    start_component_id: Optional[str] = Query(None),
    log_builds: bool = Query(True),
    flow_name: Optional[str] = Query(None),
    event_delivery: EventDeliveryType = Query(EventDeliveryType.POLLING),
):
    """Save original request as-is for worker execution while keeping FastAPI contract."""
    # Capture raw body to preserve original payload (including unknown keys)
    body_data: dict[str, Any] = {}
    body_bytes = await request.body()
    if body_bytes:
        try:
            body_data = json.loads(body_bytes)
        except json.JSONDecodeError:
            body_data = {}

    # Fallback to reconstructed body if empty (e.g., when no body provided)
    if not body_data:
        reconstructed_body: dict[str, Any] = {}
        if inputs:
            reconstructed_body["inputs"] = inputs.model_dump(exclude_none=True)
        if data:
            reconstructed_body["data"] = data.model_dump(exclude_none=True)
        if reconstructed_body:
            body_data = reconstructed_body

    # Capture query parameters exactly as received
    query_params: dict[str, Any] = {}
    if request.query_params:
        for key, value in request.query_params.multi_items():
            if key in query_params:
                existing = query_params[key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    query_params[key] = [existing, value]
            else:
                query_params[key] = value

    payload: dict[str, Any] = {
        "body": body_data,
        "query_params": query_params,
    }

    task_record = build_task_record(
        endpoint=f"/api/v1/build/{flow_id}/flow",
        method="POST",
        payload=payload,
    )
    task_id = queue_connector.enqueue(task_record)
    return TaskResponse(task_id=task_id, status="pending", message=f"enqueued: {task_id}")


@app.get("/api/v1/build/{job_id}/events", tags=["langflow"])
async def get_build_events(
    job_id: str,
    request: Request,
    event_delivery: EventDeliveryType = Query(EventDeliveryType.POLLING),
):
    """Save original request as-is for worker execution while keeping FastAPI contract."""
    query_params: dict[str, Any] = {}
    for key, value in request.query_params.multi_items():
        if key in query_params:
            existing = query_params[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                query_params[key] = [existing, value]
        else:
            query_params[key] = value

    if not query_params and event_delivery:
        query_params["event_delivery"] = event_delivery.value

    payload: dict[str, Any] = {
        "query_params": query_params,
    }

    task_record = build_task_record(
        endpoint=f"/api/v1/build/{job_id}/events",
        method="GET",
        payload=payload,
    )
    task_id = queue_connector.enqueue(task_record)
    return TaskResponse(task_id=task_id, status="pending", message=f"enqueued: {task_id}")


@app.get("/parse_task_events/{task_id}", tags=["internal"])
def parse_task_events(task_id: str):
    task_record = queue_connector.get_task(task_id)
    if not task_record:
        raise HTTPException(status_code=404, detail="Task not found")

    parsed_response = _parse_response_events(task_record.get("response"))

    return {
        "task_id": task_id,
        "status": task_record.get("status"),
        "request": task_record.get("request"),
        "response": {
            "status_code": parsed_response["status_code"],
            "events": parsed_response["events"],
            "raw_text": parsed_response["raw_text"],
        },
    }


@app.get("/health", tags=["internal"])
def health():
    try:
        queue_connector.ping()
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
