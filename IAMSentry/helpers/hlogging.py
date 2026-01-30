"""Logging utilities for IAMSentry.

This module provides logging helper functions including:
- Logger factory with namespace support
- Structured JSON logging for log aggregation
- Sensitive data obfuscation for safe logging

Example:
    >>> from IAMSentry.helpers import hlogging
    >>> _log = hlogging.get_logger(__name__)
    >>> _log.info('Processing started')

    >>> # Enable structured logging for production
    >>> hlogging.configure_structured_logging()
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any, Dict, Optional

__all__ = [
    "get_logger",
    "configure_logging",
    "configure_structured_logging",
    "obfuscated",
    "log_with_context",
]

# Track if logging has been configured
_logging_configured = False


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs logs in JSON format suitable for log aggregation systems
    like ELK, Splunk, or Google Cloud Logging.

    Example output:
        {"timestamp": "2024-01-15T10:30:00Z", "level": "INFO",
         "logger": "IAMSentry.cli", "message": "Scan started", "project": "my-project"}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Arguments:
            record: The log record to format.

        Returns:
            JSON-formatted log string.
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info
        if record.pathname:
            log_data["file"] = record.pathname
            log_data["line"] = record.lineno

        # Add process/thread info
        log_data["process"] = record.process
        log_data["thread"] = record.threadName

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message"
            ):
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Arguments:
        name: The name for the logger, typically ``__name__``.

    Returns:
        A configured logging.Logger instance.

    Example:
        >>> from IAMSentry.helpers import hlogging
        >>> _log = hlogging.get_logger(__name__)
        >>> _log.info('Processing started')
    """
    return logging.getLogger(name)


def configure_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Configure logging from a configuration dictionary.

    Arguments:
        config: A logging configuration dictionary compatible with
            logging.config.dictConfig(). If None, uses basic configuration.

    Example:
        >>> configure_logging({
        ...     'version': 1,
        ...     'root': {'level': 'DEBUG', 'handlers': ['console']}
        ... })
    """
    global _logging_configured

    if config:
        logging.config.dictConfig(config)
    else:
        # Basic configuration if none provided
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(process)s] [%(processName)s] [%(threadName)s] '
                   '%(levelname)s %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    _logging_configured = True


def configure_structured_logging(
    level: int = logging.INFO,
    stream: Any = None
) -> None:
    """Configure structured JSON logging.

    Use this for production environments where logs are sent to
    log aggregation systems (ELK, Splunk, Cloud Logging, etc.).

    Arguments:
        level: Logging level (default: INFO).
        stream: Output stream (default: sys.stdout).

    Example:
        >>> configure_structured_logging(level=logging.DEBUG)
    """
    global _logging_configured

    if stream is None:
        stream = sys.stdout

    # Create handler with structured formatter
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)
    _logging_configured = True


def obfuscated(text: str, visible_chars: int = 2) -> str:
    """Obfuscate sensitive text for safe logging.

    This function masks the middle portion of a string, leaving only
    a few characters visible at the start and end. Useful for logging
    sensitive data like project IDs, email addresses, or account names.

    Arguments:
        text: The text to obfuscate.
        visible_chars: Number of characters to show at start and end.
            Defaults to 2.

    Returns:
        Obfuscated string with middle portion replaced by asterisks.

    Examples:
        >>> obfuscated('my-project-id')
        'my**********id'
        >>> obfuscated('user@example.com')
        'us************om'
        >>> obfuscated('short')
        'sh*rt'
        >>> obfuscated('ab')
        '**'
        >>> obfuscated('')
        ''
    """
    if not text:
        return ''

    text_str = str(text)
    length = len(text_str)

    # For very short strings, just show asterisks
    if length <= visible_chars * 2:
        return '*' * length

    # Show first and last visible_chars, mask the middle
    start = text_str[:visible_chars]
    end = text_str[-visible_chars:]
    middle_length = length - (visible_chars * 2)

    return start + ('*' * middle_length) + end


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any
) -> None:
    """Log a message with additional context fields.

    Useful for structured logging where you want to add extra fields
    to the log record.

    Arguments:
        logger: The logger instance to use.
        level: Logging level (e.g., logging.INFO).
        message: The log message.
        **context: Additional context fields to include in the log.

    Example:
        >>> log_with_context(
        ...     _log, logging.INFO, "Scan completed",
        ...     project="my-project", duration_ms=1500
        ... )
    """
    extra = {key: value for key, value in context.items()}
    logger.log(level, message, extra=extra)
