import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 128

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

STANDARD_LOG_RECORD_FIELDS = set(
    logging.LogRecord("", logging.INFO, "", 0, "", (), None).__dict__
) | {"asctime", "message"}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }

        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_RECORD_FIELDS and not key.startswith("_") and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(log_level: str) -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler(sys.stdout))

    for handler in root_logger.handlers:
        handler.setFormatter(JsonLogFormatter())

    root_logger.setLevel(_level_for(log_level))


def request_id_from_header(header_value: Optional[str]) -> str:
    candidate = (header_value or "").strip()
    if _valid_request_id(candidate):
        return candidate
    return uuid.uuid4().hex


def _valid_request_id(candidate: str) -> bool:
    return (
        bool(candidate)
        and len(candidate) <= MAX_REQUEST_ID_LENGTH
        and all(character.isprintable() and character not in "\r\n" for character in candidate)
    )


def _level_for(log_level: str) -> int:
    return getattr(logging, log_level.upper(), logging.INFO)
