"""Logging utilities for IAMSentry.

This module provides logging helper functions including:
- Logger factory with namespace support
- Structured JSON logging for log aggregation
- Sensitive data obfuscation for safe logging
- Environment-based auto-configuration

Environment Variables:
    IAMSENTRY_LOG_FORMAT: "json" for structured logging, "text" for human-readable (default: text)
    IAMSENTRY_LOG_LEVEL: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)
    IAMSENTRY_LOG_FILE: Optional file path to write logs to
    IAMSENTRY_LOG_INCLUDE_LOCATION: Include file/line in JSON logs (default: false)

Example:
    >>> from IAMSentry.helpers import hlogging
    >>> _log = hlogging.get_logger(__name__)
    >>> _log.info('Processing started')

    >>> # Enable structured logging for production
    >>> hlogging.configure_structured_logging()

    >>> # Or use environment variables:
    >>> # export IAMSENTRY_LOG_FORMAT=json
    >>> # export IAMSENTRY_LOG_LEVEL=DEBUG
"""

import json
import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

__all__ = [
    "get_logger",
    "configure_logging",
    "configure_structured_logging",
    "configure_from_env",
    "obfuscated",
    "log_with_context",
    "StructuredFormatter",
]

# Track if logging has been configured
_logging_configured = False

# Environment variable configuration
_LOG_FORMAT = os.environ.get("IAMSENTRY_LOG_FORMAT", "text").lower()
_LOG_LEVEL = os.environ.get("IAMSENTRY_LOG_LEVEL", "INFO").upper()
_LOG_FILE = os.environ.get("IAMSENTRY_LOG_FILE", "")
_LOG_INCLUDE_LOCATION = os.environ.get("IAMSENTRY_LOG_INCLUDE_LOCATION", "false").lower() == "true"


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs logs in JSON format suitable for log aggregation systems
    like ELK, Splunk, Datadog, or Google Cloud Logging.

    Features:
    - ISO 8601 timestamps with timezone
    - Correlation ID support for request tracing
    - Exception formatting with stack traces
    - Extra field passthrough for context

    Example output:
        {"timestamp": "2024-01-15T10:30:00.123Z", "level": "INFO",
         "logger": "IAMSentry.cli", "message": "Scan started",
         "project": "my-project", "correlation_id": "abc123"}

    Arguments:
        include_location: Include file path and line number (default: from env).
        service_name: Service name to include in all logs (default: "iamsentry").
    """

    # Fields from LogRecord that we handle specially
    RESERVED_FIELDS = {
        "name",
        "msg",
        "args",
        "created",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "exc_info",
        "exc_text",
        "thread",
        "threadName",
        "message",
        "taskName",
    }

    def __init__(
        self,
        include_location: bool = None,
        service_name: str = "iamsentry",
    ):
        """Initialize the formatter.

        Arguments:
            include_location: Include file/line info (default: from IAMSENTRY_LOG_INCLUDE_LOCATION).
            service_name: Service name for all logs.
        """
        super().__init__()
        self.include_location = (
            include_location if include_location is not None else _LOG_INCLUDE_LOCATION
        )
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Arguments:
            record: The log record to format.

        Returns:
            JSON-formatted log string.
        """
        # Base fields
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Add location info if enabled
        if self.include_location and record.pathname:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add process/thread info for debugging concurrency issues
        log_data["process_id"] = record.process
        log_data["thread_name"] = record.threadName

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "traceback": self.formatException(record.exc_info),
            }

        # Add any extra fields passed via extra={} or log adapters
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_FIELDS and not key.startswith("_"):
                try:
                    # Ensure value is JSON serializable
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, default=str, ensure_ascii=False)


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
            format="%(asctime)s [%(process)s] [%(processName)s] [%(threadName)s] "
            "%(levelname)s %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    _logging_configured = True


def configure_structured_logging(level: int = logging.INFO, stream: Any = None) -> None:
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
        return ""

    text_str = str(text)
    length = len(text_str)

    # For very short strings, just show asterisks
    if length <= visible_chars * 2:
        return "*" * length

    # Show first and last visible_chars, mask the middle
    start = text_str[:visible_chars]
    end = text_str[-visible_chars:]
    middle_length = length - (visible_chars * 2)

    return start + ("*" * middle_length) + end


def log_with_context(logger: logging.Logger, level: int, message: str, **context: Any) -> None:
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


def configure_from_env() -> None:
    """Configure logging from environment variables.

    This function reads logging configuration from environment variables
    and sets up logging accordingly. Call this at application startup.

    Environment Variables:
        IAMSENTRY_LOG_FORMAT: "json" or "text" (default: text)
        IAMSENTRY_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
        IAMSENTRY_LOG_FILE: Optional file path for log output
        IAMSENTRY_LOG_INCLUDE_LOCATION: "true" to include file/line in JSON

    Example:
        >>> import os
        >>> os.environ["IAMSENTRY_LOG_FORMAT"] = "json"
        >>> os.environ["IAMSENTRY_LOG_LEVEL"] = "DEBUG"
        >>> configure_from_env()
    """
    global _logging_configured

    # Parse log level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(_LOG_LEVEL, logging.INFO)

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if _LOG_FORMAT == "json":
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

    handlers.append(console_handler)

    # File handler (if configured)
    if _LOG_FILE:
        try:
            from pathlib import Path

            log_path = Path(_LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(_LOG_FILE)

            # Always use JSON for file logs (easier to parse)
            if _LOG_FORMAT == "json":
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )

            handlers.append(file_handler)
        except Exception as e:
            # Don't fail if file logging setup fails
            sys.stderr.write(f"Warning: Could not configure file logging: {e}\n")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    # Add new handlers
    for handler in handlers:
        handler.setLevel(level)
        root_logger.addHandler(handler)

    _logging_configured = True

    # Log configuration (only if debug)
    if level == logging.DEBUG:
        root_logger.debug(
            "Logging configured: format=%s, level=%s, file=%s",
            _LOG_FORMAT,
            _LOG_LEVEL,
            _LOG_FILE or "(none)",
        )


def is_json_logging_enabled() -> bool:
    """Check if JSON logging is enabled.

    Returns:
        True if IAMSENTRY_LOG_FORMAT is set to "json".
    """
    return _LOG_FORMAT == "json"


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that adds persistent context to all log messages.

    Useful for adding request IDs, user info, or other context that should
    appear in all logs within a scope.

    Example:
        >>> base_logger = get_logger(__name__)
        >>> logger = ContextLogger(base_logger, {"request_id": "abc123", "user": "admin"})
        >>> logger.info("Processing request")
        # Output includes request_id and user in every log
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process the logging call to add context.

        Arguments:
            msg: The log message.
            kwargs: Keyword arguments for the log call.

        Returns:
            Tuple of (message, kwargs) with extra context added.
        """
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(name: str, **context: Any) -> ContextLogger:
    """Get a logger with persistent context fields.

    Arguments:
        name: Logger name (typically __name__).
        **context: Context fields to include in all logs.

    Returns:
        ContextLogger instance.

    Example:
        >>> logger = get_context_logger(__name__, request_id="abc123")
        >>> logger.info("Request started")  # Includes request_id
        >>> logger.info("Request completed")  # Also includes request_id
    """
    base_logger = get_logger(name)
    return ContextLogger(base_logger, context)
