#!/usr/bin/env python3
"""Analyze actual permission usage from GCP audit logs.

Uses 400-day retention period vs 90-day IAM recommender window to provide
more comprehensive permission usage analysis.

Security Note:
    This module uses subprocess to call gcloud CLI. All inputs are validated
    to prevent command injection attacks.
"""

import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from IAMSentry.helpers import hlogging

_log = hlogging.get_logger(__name__)

# Validation patterns
SERVICE_ACCOUNT_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.iam\.gserviceaccount\.com$"
)
PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")


class InputValidationError(ValueError):
    """Raised when input validation fails."""

    pass


def validate_service_account(email: str) -> str:
    """Validate service account email format.

    Arguments:
        email: Service account email to validate.

    Returns:
        The validated email.

    Raises:
        InputValidationError: If email format is invalid.
    """
    if not email:
        raise InputValidationError("Service account email cannot be empty")

    # Check length
    if len(email) > 256:
        raise InputValidationError("Service account email too long")

    # Check format
    if not SERVICE_ACCOUNT_PATTERN.match(email):
        raise InputValidationError(
            f"Invalid service account email format: {hlogging.obfuscated(email)}. "
            "Expected format: name@project.iam.gserviceaccount.com"
        )

    return email


def validate_project_id(project_id: str) -> str:
    """Validate GCP project ID format.

    Arguments:
        project_id: Project ID to validate.

    Returns:
        The validated project ID.

    Raises:
        InputValidationError: If project ID format is invalid.
    """
    if not project_id:
        raise InputValidationError("Project ID cannot be empty")

    # Check length
    if len(project_id) > 30:
        raise InputValidationError("Project ID too long (max 30 characters)")

    # Check format
    if not PROJECT_ID_PATTERN.match(project_id):
        raise InputValidationError(
            f"Invalid project ID format: {project_id}. "
            "Must be 6-30 lowercase letters, digits, or hyphens. "
            "Must start with a letter and cannot end with a hyphen."
        )

    return project_id


def validate_days_back(days: int) -> int:
    """Validate days_back parameter.

    Arguments:
        days: Number of days to look back.

    Returns:
        The validated days value.

    Raises:
        InputValidationError: If days is out of valid range.
    """
    if not isinstance(days, int):
        raise InputValidationError("days_back must be an integer")

    if days < 1:
        raise InputValidationError("days_back must be at least 1")

    if days > 400:
        raise InputValidationError("days_back cannot exceed 400 (Cloud Logging retention limit)")

    return days


def validate_max_results(max_results: int) -> int:
    """Validate max_results parameter.

    Arguments:
        max_results: Maximum number of results to return.

    Returns:
        The validated max_results value.

    Raises:
        InputValidationError: If max_results is out of valid range.
    """
    if not isinstance(max_results, int):
        raise InputValidationError("max_results must be an integer")

    if max_results < 1:
        raise InputValidationError("max_results must be at least 1")

    if max_results > 10000:
        raise InputValidationError("max_results cannot exceed 10000")

    return max_results


class AuditLogPermissionAnalyzer:
    """Analyze GCP audit logs for actual permission usage.

    This class queries Cloud Logging to determine what permissions
    a service account has actually used, providing data beyond the
    90-day window of IAM Recommender.

    Attributes:
        project_id: GCP project ID to query.
        rate_limit_delay: Seconds to wait between queries.

    Example:
        >>> analyzer = AuditLogPermissionAnalyzer('my-project')
        >>> result = analyzer.analyze_service_account(
        ...     'sa@my-project.iam.gserviceaccount.com',
        ...     days_back=400
        ... )
    """

    def __init__(self, project_id: str, rate_limit_delay: int = 2):
        """Initialize the analyzer.

        Arguments:
            project_id: GCP project ID to query.
            rate_limit_delay: Seconds to wait between queries (default: 2).

        Raises:
            InputValidationError: If project_id is invalid.
        """
        self.project_id = validate_project_id(project_id)
        self.rate_limit_delay = max(0, min(rate_limit_delay, 60))  # Cap at 60s

        # Verify gcloud is available
        if not shutil.which("gcloud"):
            raise RuntimeError("gcloud CLI not found. Please install the Google Cloud SDK.")

    def query_audit_logs(
        self, service_account: str, days_back: int = 400, max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query audit logs for a specific service account.

        Arguments:
            service_account: Service account email to query.
            days_back: Number of days to look back (max 400).
            max_results: Maximum number of log entries to return.

        Returns:
            List of log entry dictionaries.

        Raises:
            InputValidationError: If any input is invalid.
        """
        # Validate all inputs
        service_account = validate_service_account(service_account)
        days_back = validate_days_back(days_back)
        max_results = validate_max_results(max_results)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Format timestamps
        start_timestamp = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_timestamp = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        _log.info(
            "Querying audit logs for %s from %s to %s",
            hlogging.obfuscated(service_account),
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        # Build the logging query filter
        # Note: We use a simple filter that gcloud can handle safely
        query_filter = (
            f'protoPayload.authenticationInfo.principalEmail="{service_account}" '
            f'AND timestamp>="{start_timestamp}" '
            f'AND timestamp<="{end_timestamp}"'
        )

        # Build command as argument list (NOT shell string) to prevent injection
        cmd = [
            "gcloud",
            "logging",
            "read",
            query_filter,
            f"--project={self.project_id}",
            f"--limit={max_results}",
            "--format=json",
        ]

        try:
            # SECURITY: shell=False prevents command injection
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                shell=False,  # CRITICAL: Never use shell=True with user input
            )

            if result.returncode != 0:
                # Don't log full stderr as it may contain sensitive info
                _log.warning(
                    "Error querying logs for %s (exit code %d)",
                    hlogging.obfuscated(service_account),
                    result.returncode,
                )
                return []

            if result.stdout.strip():
                return json.loads(result.stdout)
            else:
                _log.info("No audit log entries found for %s", hlogging.obfuscated(service_account))
                return []

        except subprocess.TimeoutExpired:
            _log.warning("Query timeout for %s", hlogging.obfuscated(service_account))
            return []
        except json.JSONDecodeError as e:
            _log.warning(
                "Failed to parse JSON response for %s: %s",
                hlogging.obfuscated(service_account),
                type(e).__name__,
            )
            return []

    def extract_permissions_from_logs(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract actual permissions used from audit log entries.

        Arguments:
            log_entries: List of audit log entries.

        Returns:
            Dictionary containing:
                - permissions_used: List of permission strings
                - api_calls: Dict of API call counts
                - services_used: List of service names
                - total_api_calls: Total number of API calls
                - unique_api_calls: Number of unique API calls
        """
        permissions_used = set()
        api_calls: Counter = Counter()
        services_used = set()

        for entry in log_entries:
            if "protoPayload" not in entry:
                continue

            payload = entry["protoPayload"]

            # Extract method name (API call)
            if "methodName" in payload:
                method = payload["methodName"]
                api_calls[method] += 1

                # Extract service from method name
                if "." in method:
                    service = method.split(".")[0]
                    services_used.add(service)

                # Map API calls to IAM permissions
                permission = self._api_call_to_permission(method)
                if permission:
                    permissions_used.add(permission)

        return {
            "permissions_used": sorted(permissions_used),
            "api_calls": dict(api_calls.most_common(20)),
            "services_used": sorted(services_used),
            "total_api_calls": sum(api_calls.values()),
            "unique_api_calls": len(api_calls),
        }

    def _api_call_to_permission(self, method_name: str) -> Optional[str]:
        """Map GCP API calls to approximate IAM permissions.

        This is a simplified mapping - actual permissions can be more complex.

        Arguments:
            method_name: The API method name.

        Returns:
            The corresponding IAM permission, or None if not mappable.
        """
        # Common permission mappings
        permission_mappings = {
            # Compute
            "compute.instances.get": "compute.instances.get",
            "compute.instances.list": "compute.instances.list",
            "compute.instances.create": "compute.instances.create",
            "compute.instances.delete": "compute.instances.delete",
            "compute.disks.get": "compute.disks.get",
            "compute.disks.create": "compute.disks.create",
            # Storage
            "storage.objects.get": "storage.objects.get",
            "storage.objects.create": "storage.objects.create",
            "storage.objects.delete": "storage.objects.delete",
            "storage.objects.list": "storage.objects.list",
            "storage.buckets.get": "storage.buckets.get",
            # Cloud SQL
            "sql.instances.get": "cloudsql.instances.get",
            "sql.instances.connect": "cloudsql.instances.connect",
            # Logging
            "logging.logEntries.create": "logging.logEntries.create",
            "logging.logEntries.list": "logging.logEntries.list",
            # Monitoring
            "monitoring.timeSeries.create": "monitoring.timeSeries.create",
            "monitoring.metricDescriptors.create": "monitoring.metricDescriptors.create",
            # Artifact Registry
            "artifactregistry.repositories.downloadArtifacts": "artifactregistry.repositories.downloadArtifacts",
            "artifactregistry.repositories.uploadArtifacts": "artifactregistry.repositories.uploadArtifacts",
            # Secret Manager
            "secretmanager.versions.access": "secretmanager.versions.access",
            # Resource Manager
            "cloudresourcemanager.projects.get": "resourcemanager.projects.get",
        }

        # Direct mapping
        if method_name in permission_mappings:
            return permission_mappings[method_name]

        # Pattern-based mapping for common cases
        if method_name.startswith("compute."):
            parts = method_name.split(".")
            if len(parts) >= 3:
                return f"compute.{parts[1]}.{parts[2]}"

        elif method_name.startswith("storage."):
            parts = method_name.split(".")
            if len(parts) >= 3:
                return f"storage.{parts[1]}.{parts[2]}"

        # Return the method name as approximation if no mapping found
        return method_name

    def analyze_service_account(self, service_account: str, days_back: int = 400) -> Dict[str, Any]:
        """Analyze a single service account's permission usage.

        Arguments:
            service_account: Service account email to analyze.
            days_back: Number of days to look back (max 400).

        Returns:
            Dictionary containing analysis results.

        Raises:
            InputValidationError: If service_account format is invalid.
        """
        # Validate input
        service_account = validate_service_account(service_account)
        days_back = validate_days_back(days_back)

        _log.info("Analyzing service account: %s", hlogging.obfuscated(service_account))

        # Query audit logs
        log_entries = self.query_audit_logs(service_account, days_back)

        if not log_entries:
            return {
                "service_account": service_account,
                "permissions_used": [],
                "api_calls": {},
                "services_used": [],
                "total_api_calls": 0,
                "analysis_period_days": days_back,
                "status": "no_logs_found",
            }

        # Extract permissions from logs
        analysis = self.extract_permissions_from_logs(log_entries)
        analysis["service_account"] = service_account
        analysis["analysis_period_days"] = days_back
        analysis["log_entries_found"] = len(log_entries)
        analysis["status"] = "success"

        _log.info(
            "Analysis complete for %s: %d log entries, %d unique permissions",
            hlogging.obfuscated(service_account),
            len(log_entries),
            len(analysis["permissions_used"]),
        )

        return analysis


def main():
    """CLI entry point for audit log analysis."""
    if len(sys.argv) < 2:
        print(
            "Usage: python audit_log_permission_analyzer.py <service_account_email> [days_back] [project_id]"
        )
        print(
            "Example: python audit_log_permission_analyzer.py sa@project.iam.gserviceaccount.com 400 my-project"
        )
        sys.exit(1)

    service_account = sys.argv[1]
    days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    project_id = sys.argv[3] if len(sys.argv) > 3 else None

    if not project_id:
        print("Error: project_id is required")
        sys.exit(1)

    try:
        analyzer = AuditLogPermissionAnalyzer(project_id)
        result = analyzer.analyze_service_account(service_account, days_back)

        # Print summary
        print(f"\nAnalysis Results for {hlogging.obfuscated(service_account)}:")
        print(f"  Status: {result['status']}")
        print(f"  Period: {result['analysis_period_days']} days")
        print(f"  Log entries: {result.get('log_entries_found', 0)}")
        print(f"  Total API calls: {result['total_api_calls']}")
        print(f"  Unique permissions: {len(result['permissions_used'])}")

        if result["permissions_used"]:
            print(f"\nTop Permissions Used:")
            for perm in result["permissions_used"][:10]:
                print(f"  - {perm}")

        # Save results
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", service_account)
        output_file = f"audit_analysis_{safe_name}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\nResults saved to: {output_file}")

    except InputValidationError as e:
        print(f"Validation error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"Runtime error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
