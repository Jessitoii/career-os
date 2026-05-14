import logging
import re
from typing import Any

class RedactingFormatter(logging.Formatter):
    """
    Formatter that intercepts log messages and scrubs PII and secrets
    before they are written to standard output or log files.
    """
    
    # Patterns for sensitive data
    PATTERNS = {
        "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        "PHONE": r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        "BEARER_TOKEN": r'(?i)bearer\s+[A-Za-z0-9\-\._~\+\/]+=*',
        "API_KEY": r'(?i)(api[_-]?key|secret|token)["\s:=]+[A-Za-z0-9\-\._~\+\/]{16,}',
        "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
        "OAUTH": r'(?i)oauth_token=["\']?[A-Za-z0-9\-_\.]+["\']?'
    }
    
    def __init__(self, fmt: str = None):
        super().__init__(fmt)
        self.compiled_patterns = {k: re.compile(v) for k, v in self.PATTERNS.items()}

    def format(self, record: logging.LogRecord) -> str:
        original_msg = super().format(record)
        return self.redact(original_msg)

    def redact(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        for label, pattern in self.compiled_patterns.items():
            text = pattern.sub(f'[REDACTED_{label}]', text)
        return text

def setup_secure_logging(level: int = logging.INFO):
    """Reconfigure root logger to use the RedactingFormatter."""
    root_logger = logging.getLogger()
    # Clear existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    handler = logging.StreamHandler()
    formatter = RedactingFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

def scrub_dict(data: dict) -> dict:
    """Recursively scrub sensitive keys from a dictionary (e.g., JSON payloads)."""
    sensitive_keys = {"password", "token", "secret", "authorization", "ssn", "resume_text"}
    scrubbed = {}
    for k, v in data.items():
        if any(s in k.lower() for s in sensitive_keys):
            scrubbed[k] = "[REDACTED]"
        elif isinstance(v, dict):
            scrubbed[k] = scrub_dict(v)
        else:
            scrubbed[k] = v
    return scrubbed
