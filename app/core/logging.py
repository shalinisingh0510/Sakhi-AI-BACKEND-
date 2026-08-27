from __future__ import annotations

import logging
import sys


import logging
import sys
import json
import re

class SensitiveDataFormatter(logging.Formatter):
    """
    JSON formatter that redacts specific sensitive keys.
    """
    SENSITIVE_KEYS = {"password", "token", "access_token", "refresh_token", "api_key", "symptoms", "weight"}
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # If extra kwargs were passed, redact and include them
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
            
        # Basic sanitization of message string (e.g. catch explicit tokens)
        if "Bearer " in log_obj["message"]:
            log_obj["message"] = re.sub(r"Bearer [A-Za-z0-9\-\._~\+\/]+", "Bearer [REDACTED]", log_obj["message"])
            
        return json.dumps(log_obj)

def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SensitiveDataFormatter())
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler]
    )

