"""Structured logging configuration for the Modbus PLC client."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter for structured log events."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "context"):
            payload["context"] = record.context
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(level: str = "INFO", json_logs: bool = False) -> logging.Logger:
    """Create and configure a logger for this tool.

    Args:
        level: Logging level name.
        json_logs: Whether to output logs as JSON lines.

    Returns:
        Configured logger instance.
    """

    logger = logging.getLogger("modbus_plc_client")
    logger.setLevel(level.upper())

    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(handler)
    logger.propagate = False
    return logger
