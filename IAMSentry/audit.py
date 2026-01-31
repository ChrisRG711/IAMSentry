"""Audit logging for IAMSentry.

Provides comprehensive audit trail for all IAM changes and security events.
Designed for compliance (SOC 2, etc.) with tamper-evident logging.

Features:
- Structured JSON audit logs
- Before/after state capture for IAM changes
- User/operator identification
- Configurable output (file, stdout, Cloud Logging)
- Log signing for tamper detection (optional)

Configuration via environment:
    IAMSENTRY_AUDIT_LOG_PATH: Path to audit log file (default: ./audit.log)
    IAMSENTRY_AUDIT_LOG_STDOUT: Also log to stdout (default: false)
    IAMSENTRY_AUDIT_SIGN_LOGS: Sign logs with HMAC (default: false)
    IAMSENTRY_AUDIT_SIGN_KEY: HMAC key for log signing

Example:
    >>> from IAMSentry.audit import audit_log, AuditEvent
    >>> audit_log.log_event(
    ...     event_type=AuditEvent.IAM_CHANGE,
    ...     action="REMOVE_ROLE",
    ...     resource="projects/my-project",
    ...     actor="user:admin",
    ...     details={"role": "roles/editor", "member": "sa@project.iam.gserviceaccount.com"},
    ...     before_state={"bindings": [...]},
    ...     after_state={"bindings": [...]}
    ... )
"""

import hashlib
import hmac
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from IAMSentry.helpers import hlogging

_log = hlogging.get_logger(__name__)

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "audit_log",
    "get_audit_logger",
]


class AuditEvent(str, Enum):
    """Types of audit events."""

    # Authentication events
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTH_LOGOUT = "AUTH_LOGOUT"

    # IAM events
    IAM_SCAN_START = "IAM_SCAN_START"
    IAM_SCAN_COMPLETE = "IAM_SCAN_COMPLETE"
    IAM_RECOMMENDATION_FOUND = "IAM_RECOMMENDATION_FOUND"
    IAM_CHANGE_PROPOSED = "IAM_CHANGE_PROPOSED"
    IAM_CHANGE_APPROVED = "IAM_CHANGE_APPROVED"
    IAM_CHANGE_REJECTED = "IAM_CHANGE_REJECTED"
    IAM_CHANGE_EXECUTED = "IAM_CHANGE_EXECUTED"
    IAM_CHANGE_FAILED = "IAM_CHANGE_FAILED"
    IAM_CHANGE_ROLLBACK = "IAM_CHANGE_ROLLBACK"

    # Configuration events
    CONFIG_LOADED = "CONFIG_LOADED"
    CONFIG_CHANGED = "CONFIG_CHANGED"

    # System events
    SYSTEM_START = "SYSTEM_START"
    SYSTEM_STOP = "SYSTEM_STOP"
    SYSTEM_ERROR = "SYSTEM_ERROR"

    # API events
    API_REQUEST = "API_REQUEST"
    API_ERROR = "API_ERROR"


class AuditRecord:
    """Represents a single audit log record.

    Attributes:
        id: Unique identifier for this record.
        timestamp: ISO 8601 timestamp.
        event_type: Type of audit event.
        action: Specific action performed.
        resource: Resource affected (project, account, etc.).
        actor: Who performed the action.
        details: Additional event details.
        before_state: State before the change (for IAM changes).
        after_state: State after the change (for IAM changes).
        request_id: Correlation ID for request tracing.
        client_ip: Client IP address.
        user_agent: Client user agent.
        signature: HMAC signature for tamper detection.
    """

    def __init__(
        self,
        event_type: AuditEvent,
        action: str,
        resource: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Create an audit record.

        Arguments:
            event_type: Type of audit event.
            action: Specific action performed.
            resource: Resource affected.
            actor: Who performed the action.
            details: Additional event details.
            before_state: State before change.
            after_state: State after change.
            request_id: Correlation ID.
            client_ip: Client IP address.
            user_agent: Client user agent.
        """
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type
        self.action = action
        self.resource = resource
        self.actor = actor
        self.details = details or {}
        self.before_state = before_state
        self.after_state = after_state
        self.request_id = request_id or str(uuid.uuid4())
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary.

        Returns:
            Dictionary representation of the record.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": (
                self.event_type.value
                if isinstance(self.event_type, AuditEvent)
                else self.event_type
            ),
            "action": self.action,
            "resource": self.resource,
            "actor": self.actor,
            "details": self.details,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "signature": self.signature,
        }

    def to_json(self) -> str:
        """Convert record to JSON string.

        Returns:
            JSON representation of the record.
        """
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    def compute_signature(self, key: bytes) -> str:
        """Compute HMAC signature for this record.

        Arguments:
            key: HMAC signing key.

        Returns:
            Hex-encoded HMAC-SHA256 signature.
        """
        # Create a copy without signature for signing
        data = self.to_dict()
        data.pop("signature", None)
        message = json.dumps(data, default=str, sort_keys=True).encode()
        return hmac.new(key, message, hashlib.sha256).hexdigest()


class AuditLogger:
    """Audit logger that writes structured audit records.

    Thread-safe logger that writes JSON audit records to file and/or stdout.

    Attributes:
        log_path: Path to the audit log file.
        log_to_stdout: Whether to also log to stdout.
        sign_logs: Whether to sign logs with HMAC.
        sign_key: HMAC signing key.
    """

    def __init__(
        self,
        log_path: Optional[str] = None,
        log_to_stdout: bool = False,
        sign_logs: bool = False,
        sign_key: Optional[str] = None,
    ):
        """Initialize the audit logger.

        Arguments:
            log_path: Path to audit log file. Defaults to IAMSENTRY_AUDIT_LOG_PATH.
            log_to_stdout: Whether to log to stdout.
            sign_logs: Whether to sign log entries.
            sign_key: HMAC key for signing (required if sign_logs is True).
        """
        # Load configuration from environment
        self.log_path = log_path or os.environ.get("IAMSENTRY_AUDIT_LOG_PATH", "./audit.log")
        self.log_to_stdout = (
            log_to_stdout or os.environ.get("IAMSENTRY_AUDIT_LOG_STDOUT", "false").lower() == "true"
        )
        self.sign_logs = (
            sign_logs or os.environ.get("IAMSENTRY_AUDIT_SIGN_LOGS", "false").lower() == "true"
        )

        # Load signing key
        sign_key_env = sign_key or os.environ.get("IAMSENTRY_AUDIT_SIGN_KEY")
        if self.sign_logs:
            if not sign_key_env:
                _log.warning(
                    "IAMSENTRY_AUDIT_SIGN_LOGS is enabled but no signing key provided. "
                    "Set IAMSENTRY_AUDIT_SIGN_KEY environment variable."
                )
                self.sign_logs = False
                self.sign_key = None
            else:
                self.sign_key = sign_key_env.encode()
        else:
            self.sign_key = None

        # Thread lock for file writing
        self._lock = threading.Lock()

        # Ensure log directory exists
        log_dir = Path(self.log_path).parent
        if log_dir and not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        _log.info("Audit logger initialized: %s", self.log_path)

    def log_event(
        self,
        event_type: AuditEvent,
        action: str,
        resource: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditRecord:
        """Log an audit event.

        Arguments:
            event_type: Type of audit event.
            action: Specific action performed.
            resource: Resource affected.
            actor: Who performed the action.
            details: Additional event details.
            before_state: State before change.
            after_state: State after change.
            request_id: Correlation ID.
            client_ip: Client IP address.
            user_agent: Client user agent.

        Returns:
            The created AuditRecord.
        """
        record = AuditRecord(
            event_type=event_type,
            action=action,
            resource=resource,
            actor=actor,
            details=details,
            before_state=before_state,
            after_state=after_state,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Sign the record if enabled
        if self.sign_logs and self.sign_key:
            record.signature = record.compute_signature(self.sign_key)

        # Write to file and/or stdout
        self._write_record(record)

        return record

    def log_iam_change(
        self,
        project: str,
        account_id: str,
        action: str,
        role: str,
        actor: str,
        recommendation_id: str,
        before_policy: Optional[Dict[str, Any]] = None,
        after_policy: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> AuditRecord:
        """Log an IAM policy change.

        Convenience method for logging IAM changes with proper structure.

        Arguments:
            project: GCP project ID.
            account_id: Account being modified.
            action: Action type (REMOVE_ROLE, REPLACE_ROLE, etc.).
            role: IAM role being modified.
            actor: Who initiated the change.
            recommendation_id: ID of the recommendation being applied.
            before_policy: IAM policy before change.
            after_policy: IAM policy after change.
            success: Whether the change succeeded.
            error: Error message if failed.
            request_id: Correlation ID.
            client_ip: Client IP address.

        Returns:
            The created AuditRecord.
        """
        event_type = AuditEvent.IAM_CHANGE_EXECUTED if success else AuditEvent.IAM_CHANGE_FAILED

        details = {
            "project": project,
            "account_id": account_id,
            "action": action,
            "role": role,
            "recommendation_id": recommendation_id,
            "success": success,
        }

        if error:
            details["error"] = error

        return self.log_event(
            event_type=event_type,
            action=action,
            resource=f"projects/{project}",
            actor=actor,
            details=details,
            before_state=before_policy,
            after_state=after_policy,
            request_id=request_id,
            client_ip=client_ip,
        )

    def log_scan(
        self,
        projects: List[str],
        actor: str,
        recommendation_count: int = 0,
        start: bool = True,
        request_id: Optional[str] = None,
    ) -> AuditRecord:
        """Log a scan start or completion.

        Arguments:
            projects: Projects being scanned.
            actor: Who initiated the scan.
            recommendation_count: Number of recommendations found (for completion).
            start: True for scan start, False for completion.
            request_id: Correlation ID.

        Returns:
            The created AuditRecord.
        """
        event_type = AuditEvent.IAM_SCAN_START if start else AuditEvent.IAM_SCAN_COMPLETE

        details = {
            "projects": projects,
            "recommendation_count": recommendation_count,
        }

        return self.log_event(
            event_type=event_type,
            action="SCAN_START" if start else "SCAN_COMPLETE",
            resource=f"projects/{','.join(projects[:5])}{'...' if len(projects) > 5 else ''}",
            actor=actor,
            details=details,
            request_id=request_id,
        )

    def log_auth(
        self,
        success: bool,
        username: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AuditRecord:
        """Log an authentication event.

        Arguments:
            success: Whether authentication succeeded.
            username: Username or identifier.
            client_ip: Client IP address.
            user_agent: Client user agent.
            reason: Reason for failure (if applicable).

        Returns:
            The created AuditRecord.
        """
        event_type = AuditEvent.AUTH_SUCCESS if success else AuditEvent.AUTH_FAILURE

        details = {"username": username}
        if reason:
            details["reason"] = reason

        return self.log_event(
            event_type=event_type,
            action="LOGIN" if success else "LOGIN_FAILED",
            resource="auth",
            actor=username,
            details=details,
            client_ip=client_ip,
            user_agent=user_agent,
        )

    def _write_record(self, record: AuditRecord) -> None:
        """Write a record to file and/or stdout.

        Arguments:
            record: The audit record to write.
        """
        json_line = record.to_json()

        with self._lock:
            # Write to file
            if self.log_path:
                try:
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        f.write(json_line + "\n")
                except IOError as e:
                    _log.error("Failed to write audit log: %s", e)

            # Write to stdout
            if self.log_to_stdout:
                print(f"AUDIT: {json_line}")

    def verify_record(self, record_dict: Dict[str, Any]) -> bool:
        """Verify the signature of an audit record.

        Arguments:
            record_dict: Dictionary representation of an audit record.

        Returns:
            True if signature is valid, False otherwise.
        """
        if not self.sign_logs or not self.sign_key:
            _log.warning("Log signing is not enabled, cannot verify")
            return False

        stored_signature = record_dict.get("signature")
        if not stored_signature:
            return False

        # Recompute signature
        data = record_dict.copy()
        data.pop("signature", None)
        message = json.dumps(data, default=str, sort_keys=True).encode()
        expected_signature = hmac.new(self.sign_key, message, hashlib.sha256).hexdigest()

        return hmac.compare_digest(stored_signature, expected_signature)

    def read_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEvent]] = None,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Read and filter audit logs.

        Arguments:
            start_time: Start of time range.
            end_time: End of time range.
            event_types: Filter by event types.
            actor: Filter by actor.
            resource: Filter by resource (prefix match).
            limit: Maximum number of records to return.

        Returns:
            List of matching audit records.
        """
        if not Path(self.log_path).exists():
            return []

        results = []
        event_type_values = {e.value for e in event_types} if event_types else None

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if len(results) >= limit:
                    break

                try:
                    record = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                # Apply filters
                if start_time:
                    record_time = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                    if record_time < start_time:
                        continue

                if end_time:
                    record_time = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                    if record_time > end_time:
                        continue

                if event_type_values and record.get("event_type") not in event_type_values:
                    continue

                if actor and record.get("actor") != actor:
                    continue

                if resource and not record.get("resource", "").startswith(resource):
                    continue

                results.append(record)

        return results


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance.

    Returns:
        The AuditLogger instance.
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience alias
audit_log = property(lambda self: get_audit_logger())


# Module-level convenience functions
def log_iam_change(*args, **kwargs) -> AuditRecord:
    """Log an IAM change. See AuditLogger.log_iam_change for details."""
    return get_audit_logger().log_iam_change(*args, **kwargs)


def log_scan(*args, **kwargs) -> AuditRecord:
    """Log a scan event. See AuditLogger.log_scan for details."""
    return get_audit_logger().log_scan(*args, **kwargs)


def log_auth(*args, **kwargs) -> AuditRecord:
    """Log an auth event. See AuditLogger.log_auth for details."""
    return get_audit_logger().log_auth(*args, **kwargs)


def log_event(*args, **kwargs) -> AuditRecord:
    """Log a generic event. See AuditLogger.log_event for details."""
    return get_audit_logger().log_event(*args, **kwargs)
