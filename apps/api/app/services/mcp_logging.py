import json
import time
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from app.database import SessionLocal
from app.models import McpCallLog


def _summary(result: Any) -> str:
    try:
        text = json.dumps(result, default=str, ensure_ascii=False)
    except TypeError:
        text = str(result)
    return text[:800]


def log_mcp_call(
    tool_name: str,
    restaurant_id: str | None,
    request_json: dict,
    status: str,
    response_summary: str | None,
    error_message: str | None,
    latency_ms: int,
) -> None:
    db = SessionLocal()
    try:
        db.add(
            McpCallLog(
                tool_name=tool_name,
                restaurant_id=restaurant_id,
                request_json=request_json,
                response_summary=response_summary,
                status=status,
                error_message=error_message,
                latency_ms=latency_ms,
            )
        )
        db.commit()
    finally:
        db.close()


def run_logged_tool(tool_name: str, request_json: dict, handler: Callable) -> Any:
    started = time.perf_counter()
    restaurant_id = request_json.get("restaurant_id")
    db = SessionLocal()
    try:
        result = handler(db)
        latency = int((time.perf_counter() - started) * 1000)
        log_mcp_call(tool_name, restaurant_id, request_json, "success", _summary(result), None, latency)
        return result
    except HTTPException as exc:
        latency = int((time.perf_counter() - started) * 1000)
        log_mcp_call(tool_name, restaurant_id, request_json, "error", None, str(exc.detail), latency)
        raise
    except Exception as exc:
        latency = int((time.perf_counter() - started) * 1000)
        log_mcp_call(tool_name, restaurant_id, request_json, "error", None, str(exc), latency)
        raise
    finally:
        db.close()


def run_logged_tool_without_db(tool_name: str, request_json: dict, handler: Callable[[], Any]) -> Any:
    started = time.perf_counter()
    restaurant_id = request_json.get("restaurant_id")
    try:
        result = handler()
        latency = int((time.perf_counter() - started) * 1000)
        log_mcp_call(tool_name, restaurant_id, request_json, "success", _summary(result), None, latency)
        return result
    except HTTPException as exc:
        latency = int((time.perf_counter() - started) * 1000)
        log_mcp_call(tool_name, restaurant_id, request_json, "error", None, str(exc.detail), latency)
        raise
    except Exception as exc:
        latency = int((time.perf_counter() - started) * 1000)
        log_mcp_call(tool_name, restaurant_id, request_json, "error", None, str(exc), latency)
        raise
