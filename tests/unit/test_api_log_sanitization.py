import logging

import pytest

from summit_everything.api.app import CallbackAccessLogFilter


@pytest.mark.parametrize(
    "path",
    [
        "/callback?code=private-code&state=private-state",
        "/api/v1/integrations/feishu/callback?error=access_denied&state=private-state",
    ],
)
def test_callback_access_log_redacts_query(path: str) -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1", "GET", path, "1.1", 200),
        None,
    )

    assert CallbackAccessLogFilter().filter(record)
    rendered = record.getMessage()
    assert "private-code" not in rendered
    assert "private-state" not in rendered
    assert "access_denied" not in rendered
    assert "?[redacted]" in rendered


def test_non_callback_access_log_is_unchanged() -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1", "GET", "/api/v1/status?detail=brief", "1.1", 200),
        None,
    )

    CallbackAccessLogFilter().filter(record)

    assert "/api/v1/status?detail=brief" in record.getMessage()
