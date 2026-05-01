# src/rosa/tool_trace_logger.py
import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Dict

from langchain_core.callbacks import BaseCallbackHandler


_trace_query_id: ContextVar[str] = ContextVar("trace_query_id", default="")
_trace_tool_start_ts: ContextVar[Dict[str, float]] = ContextVar(
    "trace_tool_start_ts", default={}
)


def set_trace_query_id(query_id: str) -> None:
    _trace_query_id.set(query_id)


def get_trace_query_id() -> str:
    return _trace_query_id.get()


def new_query_id() -> str:
    return f"q_{uuid.uuid4().hex[:12]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_dir = os.getenv("ROSA_TRACE_LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, filename)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=int(os.getenv("ROSA_TRACE_MAX_BYTES", 5 * 1024 * 1024)),
        backupCount=int(os.getenv("ROSA_TRACE_BACKUP_COUNT", 3)),
        encoding="utf-8",
    )
    logger.setLevel(logging.INFO)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_trace_loggers() -> Dict[str, logging.Logger]:
    return {
        "session": _build_logger("rosa.session", "rosa_session.jsonl"),
        "tools": _build_logger("rosa.tools", "rosa_tools.jsonl"),
    }


def _truncate(s: Any, n: int = 120) -> str:
    text = str(s)
    return text if len(text) <= n else text[:n] + "...<truncated>"


def _summarize_tool_input(input_str: Any) -> Dict[str, Any]:
    # input_str 往往是字符串，这里只做简要预览
    return {"preview": _truncate(input_str, 200)}


def log_json(logger: logging.Logger, payload: Dict[str, Any]) -> None:
    logger.info(json.dumps({"ts": _utc_now(), **payload}, ensure_ascii=False))


class ToolTraceCallbackHandler(BaseCallbackHandler):
    def __init__(self, loggers: Dict[str, logging.Logger]):
        self.tools_logger = loggers["tools"]

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        #run_id = kwargs.get("run_id")
        #parent_run_id = kwargs.get("parent_run_id")

        tool_name = serialized.get("name", "unknown_tool")
        #key = str(run_id) if run_id else f"unknown_{time.time()}"

        starts = dict(_trace_tool_start_ts.get())
        #starts[key] = time.time()
        _trace_tool_start_ts.set(starts)

        log_json(
            self.tools_logger,
            {
                "event": "tool_start",
                "query_id": get_trace_query_id(),
                "tool_name": tool_name,
                "tool_input_summary": _summarize_tool_input(input_str),
                #"run_id": key,
                #"parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
        )

    def on_tool_end(self, output: Any, **kwargs) -> None:
        #run_id = kwargs.get("run_id")
        #parent_run_id = kwargs.get("parent_run_id")
        #key = str(run_id) if run_id else ""

        starts = dict(_trace_tool_start_ts.get())
        #start_ts = starts.pop(key, None)
        _trace_tool_start_ts.set(starts)

        #latency_ms = int((time.time() - start_ts) * 1000) if start_ts else None

        log_json(
            self.tools_logger,
            {
                "event": "tool_end",
                "query_id": get_trace_query_id(),
                "tool_name": kwargs.get("name", "unknown_tool"),
                #"latency_ms": latency_ms,
                "status": "ok",
                #"run_id": key,
                #"parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
        )

    def on_tool_error(self, error: BaseException, **kwargs) -> None:
        run_id = kwargs.get("run_id")
        parent_run_id = kwargs.get("parent_run_id")

        log_json(
            self.tools_logger,
            {
                "event": "tool_error",
                #"query_id": get_trace_query_id(),
                "tool_name": kwargs.get("name", "unknown_tool"),
                "status": "error",
                "error": _truncate(str(error), 200),
                "run_id": str(run_id) if run_id else None,
                #"parent_run_id": str(parent_run_id) if parent_run_id else None,
            },
        )
