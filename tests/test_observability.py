import json
import logging
import sys

from app.observability import JsonLogFormatter, configure_logging


def test_json_log_formatter_includes_exception_details() -> None:
    formatter = JsonLogFormatter()

    try:
        raise RuntimeError("formatter failure")
    except RuntimeError:
        record = logging.getLogger("andela.test").makeRecord(
            name="andela.test",
            level=logging.ERROR,
            fn=__file__,
            lno=12,
            msg="request_failed",
            args=(),
            exc_info=sys.exc_info(),
            extra={"event": "request_failed"},
        )

    payload = json.loads(formatter.format(record))

    assert payload["event"] == "request_failed"
    assert "RuntimeError: formatter failure" in payload["exception"]


def test_configure_logging_adds_stdout_handler_when_root_has_none() -> None:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    for handler in original_handlers:
        root_logger.removeHandler(handler)

    try:
        configure_logging("debug")

        assert root_logger.handlers
        assert isinstance(root_logger.handlers[0].formatter, JsonLogFormatter)
        assert root_logger.level == logging.DEBUG
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)
