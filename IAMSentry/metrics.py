"""Prometheus metrics for IAMSentry.

This module provides application metrics for monitoring IAMSentry in production.
Metrics are exposed at /metrics endpoint when the dashboard is running.

Usage:
    from IAMSentry.metrics import (
        SCAN_DURATION,
        SCAN_TOTAL,
        RECOMMENDATIONS_TOTAL,
        record_scan,
    )

    # Record a scan
    with SCAN_DURATION.labels(project="my-project").time():
        # ... perform scan ...
        pass

    # Or use the helper
    record_scan(project="my-project", duration=10.5, recommendations=25)

Environment Variables:
    IAMSENTRY_METRICS_ENABLED: Set to "false" to disable metrics (default: true)
    IAMSENTRY_METRICS_PREFIX: Custom prefix for metric names (default: "iamsentry")
"""

import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Optional

# Check if prometheus_client is available
_PROMETHEUS_AVAILABLE = False
_METRICS_ENABLED = os.environ.get("IAMSENTRY_METRICS_ENABLED", "true").lower() != "false"
_METRICS_PREFIX = os.environ.get("IAMSENTRY_METRICS_PREFIX", "iamsentry")

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    # Create dummy classes if prometheus_client not installed
    class _DummyMetric:
        """Dummy metric that does nothing when prometheus_client is unavailable."""
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def time(self):
            return _dummy_context()

        def info(self, *args, **kwargs):
            pass

    @contextmanager
    def _dummy_context():
        yield

    Counter = Gauge = Histogram = Info = _DummyMetric
    REGISTRY = None

    def generate_latest(registry=None):
        return b"# prometheus_client not installed\n"

    CONTENT_TYPE_LATEST = "text/plain"


# ============================================
# Application Info
# ============================================

APP_INFO = Info(
    f"{_METRICS_PREFIX}_app",
    "IAMSentry application information",
)

if _PROMETHEUS_AVAILABLE and _METRICS_ENABLED:
    from IAMSentry.constants import VERSION
    APP_INFO.info({
        "version": VERSION,
        "metrics_prefix": _METRICS_PREFIX,
    })


# ============================================
# Scan Metrics
# ============================================

SCAN_TOTAL = Counter(
    f"{_METRICS_PREFIX}_scans_total",
    "Total number of scans performed",
    ["project", "status"],  # status: success, error, timeout
)

SCAN_DURATION = Histogram(
    f"{_METRICS_PREFIX}_scan_duration_seconds",
    "Time spent performing scans",
    ["project"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],  # up to 10 minutes
)

SCAN_IN_PROGRESS = Gauge(
    f"{_METRICS_PREFIX}_scans_in_progress",
    "Number of scans currently running",
)


# ============================================
# Recommendation Metrics
# ============================================

RECOMMENDATIONS_TOTAL = Counter(
    f"{_METRICS_PREFIX}_recommendations_total",
    "Total recommendations processed",
    ["project", "account_type", "action"],  # action: REMOVE_ROLE, REPLACE_ROLE
)

RECOMMENDATIONS_BY_RISK = Gauge(
    f"{_METRICS_PREFIX}_recommendations_by_risk",
    "Current recommendations by risk level",
    ["risk_level"],  # critical, high, medium, low
)

RISK_SCORE_HISTOGRAM = Histogram(
    f"{_METRICS_PREFIX}_risk_score",
    "Distribution of risk scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)


# ============================================
# Remediation Metrics
# ============================================

REMEDIATION_TOTAL = Counter(
    f"{_METRICS_PREFIX}_remediations_total",
    "Total remediation actions attempted",
    ["project", "action", "status", "dry_run"],  # status: success, error, skipped
)

REMEDIATION_DURATION = Histogram(
    f"{_METRICS_PREFIX}_remediation_duration_seconds",
    "Time spent performing remediations",
    ["project"],
    buckets=[0.5, 1, 2, 5, 10, 30],
)


# ============================================
# Authentication Metrics
# ============================================

AUTH_ATTEMPTS_TOTAL = Counter(
    f"{_METRICS_PREFIX}_auth_attempts_total",
    "Total authentication attempts",
    ["method", "status"],  # method: api_key, basic, iap; status: success, failure
)

AUTH_FAILURES_TOTAL = Counter(
    f"{_METRICS_PREFIX}_auth_failures_total",
    "Total authentication failures",
    ["method", "reason"],  # reason: invalid_key, invalid_password, expired, etc.
)


# ============================================
# API Metrics
# ============================================

API_REQUESTS_TOTAL = Counter(
    f"{_METRICS_PREFIX}_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

API_REQUEST_DURATION = Histogram(
    f"{_METRICS_PREFIX}_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
)

API_ERRORS_TOTAL = Counter(
    f"{_METRICS_PREFIX}_api_errors_total",
    "Total API errors",
    ["method", "endpoint", "error_type"],
)


# ============================================
# GCP API Metrics
# ============================================

GCP_API_CALLS_TOTAL = Counter(
    f"{_METRICS_PREFIX}_gcp_api_calls_total",
    "Total GCP API calls",
    ["service", "method", "status"],  # service: recommender, cloudresourcemanager
)

GCP_API_DURATION = Histogram(
    f"{_METRICS_PREFIX}_gcp_api_duration_seconds",
    "GCP API call duration",
    ["service", "method"],
    buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30],
)

GCP_API_ERRORS_TOTAL = Counter(
    f"{_METRICS_PREFIX}_gcp_api_errors_total",
    "Total GCP API errors",
    ["service", "method", "error_code"],
)


# ============================================
# Helper Functions
# ============================================

def record_scan(
    project: str,
    duration: float,
    recommendations: int,
    status: str = "success",
) -> None:
    """Record metrics for a completed scan.

    Arguments:
        project: The GCP project scanned.
        duration: Scan duration in seconds.
        recommendations: Number of recommendations found.
        status: Scan status (success, error, timeout).
    """
    SCAN_TOTAL.labels(project=project, status=status).inc()
    SCAN_DURATION.labels(project=project).observe(duration)


def record_recommendation(
    project: str,
    account_type: str,
    action: str,
    risk_score: int,
) -> None:
    """Record metrics for a processed recommendation.

    Arguments:
        project: The GCP project.
        account_type: Type of account (user, group, serviceAccount).
        action: Recommended action (REMOVE_ROLE, REPLACE_ROLE).
        risk_score: Calculated risk score (0-100).
    """
    RECOMMENDATIONS_TOTAL.labels(
        project=project,
        account_type=account_type,
        action=action,
    ).inc()
    RISK_SCORE_HISTOGRAM.observe(risk_score)


def record_remediation(
    project: str,
    action: str,
    status: str,
    dry_run: bool,
    duration: float,
) -> None:
    """Record metrics for a remediation action.

    Arguments:
        project: The GCP project.
        action: Remediation action taken.
        status: Result status (success, error, skipped).
        dry_run: Whether this was a dry run.
        duration: Time taken in seconds.
    """
    REMEDIATION_TOTAL.labels(
        project=project,
        action=action,
        status=status,
        dry_run=str(dry_run).lower(),
    ).inc()
    REMEDIATION_DURATION.labels(project=project).observe(duration)


def record_auth_attempt(
    method: str,
    success: bool,
    reason: Optional[str] = None,
) -> None:
    """Record an authentication attempt.

    Arguments:
        method: Auth method (api_key, basic, iap).
        success: Whether authentication succeeded.
        reason: Failure reason if not successful.
    """
    status = "success" if success else "failure"
    AUTH_ATTEMPTS_TOTAL.labels(method=method, status=status).inc()

    if not success and reason:
        AUTH_FAILURES_TOTAL.labels(method=method, reason=reason).inc()


def record_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
) -> None:
    """Record an API request.

    Arguments:
        method: HTTP method (GET, POST, etc.).
        endpoint: API endpoint path.
        status_code: HTTP response status code.
        duration: Request duration in seconds.
    """
    API_REQUESTS_TOTAL.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
    ).inc()
    API_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def get_metrics() -> bytes:
    """Generate Prometheus metrics output.

    Returns:
        Prometheus metrics in text format.
    """
    if not _PROMETHEUS_AVAILABLE or not _METRICS_ENABLED:
        return b"# Prometheus metrics disabled or prometheus_client not installed\n"

    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get the content type for metrics output.

    Returns:
        Content type string for Prometheus metrics.
    """
    return CONTENT_TYPE_LATEST


def is_metrics_enabled() -> bool:
    """Check if metrics are enabled.

    Returns:
        True if metrics collection is enabled.
    """
    return _PROMETHEUS_AVAILABLE and _METRICS_ENABLED


@contextmanager
def track_scan(project: str):
    """Context manager to track scan metrics.

    Usage:
        with track_scan("my-project") as tracker:
            # ... perform scan ...
            tracker.set_recommendations(25)

    Arguments:
        project: The GCP project being scanned.

    Yields:
        ScanTracker object for recording results.
    """
    class ScanTracker:
        def __init__(self):
            self.recommendations = 0
            self.status = "success"

        def set_recommendations(self, count: int):
            self.recommendations = count

        def set_error(self):
            self.status = "error"

    tracker = ScanTracker()
    SCAN_IN_PROGRESS.inc()
    start_time = time.time()

    try:
        yield tracker
    except Exception:
        tracker.set_error()
        raise
    finally:
        duration = time.time() - start_time
        SCAN_IN_PROGRESS.dec()
        record_scan(
            project=project,
            duration=duration,
            recommendations=tracker.recommendations,
            status=tracker.status,
        )


def metrics_middleware(func: Callable) -> Callable:
    """Decorator to add metrics tracking to API endpoints.

    Usage:
        @app.get("/api/example")
        @metrics_middleware
        async def example_endpoint():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status_code = 200

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            # Extract endpoint from function name
            endpoint = f"/api/{func.__name__}"
            record_api_request(
                method="GET",  # This is simplified; real impl would get from request
                endpoint=endpoint,
                status_code=status_code,
                duration=duration,
            )

    return wrapper
