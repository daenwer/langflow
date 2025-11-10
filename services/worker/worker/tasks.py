import asyncio
import os
import httpx

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://langflow:7860")
LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY", "")


def process_langflow_task(task_id: str, flow_id: str, input_data: dict) -> dict:
    """Sync wrapper for RQ worker."""
    return asyncio.run(_run(task_id, flow_id, input_data))


async def _run(task_id: str, flow_id: str, input_data: dict) -> dict:
    url = f"{LANGFLOW_URL}/api/v1/run/{flow_id}"
    headers = {}
    if LANGFLOW_API_KEY:
        headers["Authorization"] = f"Bearer {LANGFLOW_API_KEY}"

    payload = {
        "input_value": input_data.get("input_value"),
        "input_type": input_data.get("input_type", "text"),
        "tweaks": input_data.get("tweaks"),
        "session_id": input_data.get("session_id"),
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return {"task_id": task_id, "result": resp.json()}

