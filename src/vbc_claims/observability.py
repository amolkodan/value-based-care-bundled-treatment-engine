from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from vbc_claims.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    root = logging.getLogger()
    if settings.log_json:
        for h in root.handlers:
            h.setFormatter(JsonFormatter())

