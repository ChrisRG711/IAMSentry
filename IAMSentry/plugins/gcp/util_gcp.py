"""GCP authentication and API utilities with Application Default Credentials support.

This module provides flexible authentication for GCP APIs:
1. Application Default Credentials (ADC) - Recommended for local dev and GKE
2. Explicit service account key file
3. Secret Manager integration for retrieving keys securely

Features:
- Automatic retry with exponential backoff
- Configurable request timeouts
- Support for ADC and service account authentication

Usage:
    # Using ADC (recommended)
    credentials, project = get_credentials()

    # Using explicit key file
    credentials, project = get_credentials(key_file_path='/path/to/key.json')

    # Using Secret Manager
    credentials, project = get_credentials(key_file_path='gsm://project/secret-name')
"""

import json
import os
import time
from functools import wraps
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, Iterator, List, Optional, Tuple, TypeVar

try:
    import google.auth as _google_auth
except Exception:  # pragma: no cover - best-effort optional dependency

    class _MissingGoogleAuth:
        class exceptions:
            class DefaultCredentialsError(Exception):
                pass

        @staticmethod
        def default(*args, **kwargs):
            raise RuntimeError(
                "google-auth is not installed. Install with: pip install google-auth"
            )

    _google_auth = _MissingGoogleAuth()

try:
    from google.oauth2 import service_account as _service_account
except Exception:  # pragma: no cover - best-effort optional dependency

    class _MissingServiceAccount:
        class Credentials:
            @staticmethod
            def from_service_account_file(*args, **kwargs):
                raise RuntimeError(
                    "google-auth is not installed. Install with: pip install google-auth"
                )

    _service_account = _MissingServiceAccount()

try:
    from googleapiclient import discovery as _discovery
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - best-effort optional dependency

    class HttpError(Exception):
        pass

    class _MissingDiscovery:
        @staticmethod
        def build(*args, **kwargs):
            raise RuntimeError(
                "google-api-python-client is not installed. "
                "Install with: pip install google-api-python-client"
            )

    _discovery = _MissingDiscovery()

google = SimpleNamespace(auth=_google_auth)
service_account = _service_account
discovery = _discovery

if TYPE_CHECKING:  # pragma: no cover
    from google.auth.credentials import Credentials
else:
    Credentials = object

from IAMSentry.constants import (
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    API_RETRY_MULTIPLIER,
    API_TIMEOUT,
    GCP_SCOPES,
)
from IAMSentry.helpers import hlogging

_log = hlogging.get_logger(__name__)

__all__ = [
    "get_credentials",
    "build_resource",
    "get_resource_iterator",
    "set_service_account",
    "get_service_account_class",
    "outline_gcp_project",
    "retry_on_error",
]

# Type variable for generic retry decorator
T = TypeVar("T")


def retry_on_error(
    max_retries: int = API_MAX_RETRIES,
    initial_delay: float = API_RETRY_DELAY,
    multiplier: float = API_RETRY_MULTIPLIER,
    retryable_errors: Tuple[type, ...] = (HttpError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying functions with exponential backoff.

    Arguments:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        multiplier: Multiplier for exponential backoff.
        retryable_errors: Tuple of exception types to retry on.

    Returns:
        Decorated function with retry logic.

    Example:
        >>> @retry_on_error(max_retries=3)
        ... def fetch_data():
        ...     return api.get_data()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e

                    # Check if it's a retryable HTTP error
                    if isinstance(e, HttpError):
                        status = e.resp.status if hasattr(e, "resp") else 0
                        # Don't retry on client errors (4xx) except 429 (rate limit)
                        if 400 <= status < 500 and status != 429:
                            raise

                    if attempt < max_retries:
                        _log.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                            attempt + 1,
                            max_retries + 1,
                            e,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= multiplier
                    else:
                        _log.error("All %d attempts failed. Last error: %s", max_retries + 1, e)

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry logic")

        return wrapper

    return decorator


def get_credentials(
    key_file_path: Optional[str] = None, scopes: Optional[List[str]] = None
) -> Tuple[Credentials, Optional[str]]:
    """Get GCP credentials with ADC fallback.

    Authentication priority:
    1. Explicit service account key file (if provided)
    2. Secret Manager reference (if key_file_path starts with gsm://)
    3. Application Default Credentials (gcloud auth application-default login)
    4. Compute Engine/GKE metadata service

    Arguments:
        key_file_path: Optional path to service account key file,
            or gsm:// reference to retrieve from Secret Manager.
        scopes: OAuth scopes. Defaults to cloud-platform scope.

    Returns:
        Tuple of (credentials, project_id). Project may be None if
        not determinable from credentials.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: If no credentials found.
        FileNotFoundError: If key file specified but not found.

    Example:
        >>> # Using ADC
        >>> creds, project = get_credentials()
        >>>
        >>> # Using explicit key file
        >>> creds, project = get_credentials('/path/to/key.json')
        >>>
        >>> # Using Secret Manager
        >>> creds, project = get_credentials('gsm://my-project/sa-key')
    """
    scopes = scopes or GCP_SCOPES
    project_id = None

    # Option 1: Explicit key file path
    if key_file_path:
        # Check for Secret Manager reference
        if key_file_path.startswith("gsm://"):
            key_file_path = _resolve_gsm_key_file(key_file_path)
            if key_file_path is None:
                _log.warning("Failed to resolve Secret Manager reference, falling back to ADC")
            else:
                _log.debug("Resolved key file from Secret Manager")

        if key_file_path and not key_file_path.startswith("gsm://"):
            # Load from file
            if not os.path.exists(key_file_path):
                raise FileNotFoundError(f"Service account key file not found: {key_file_path}")

            credentials = service_account.Credentials.from_service_account_file(
                key_file_path, scopes=scopes
            )

            # Extract project ID from key file
            try:
                with open(key_file_path, "r") as f:
                    key_data = json.load(f)
                    project_id = key_data.get("project_id")
            except Exception as e:
                _log.warning("Could not read project_id from key file: %s", e)

            _log.debug("Using service account credentials from: %s", key_file_path)
            return credentials, project_id

    # Option 2: Application Default Credentials
    try:
        credentials, project_id = google.auth.default(scopes=scopes)
        _log.debug("Using Application Default Credentials (project: %s)", project_id)
        return credentials, project_id
    except google.auth.exceptions.DefaultCredentialsError as e:
        _log.error(
            "No credentials found. Either provide key_file_path or run: "
            "gcloud auth application-default login"
        )
        raise


def _resolve_gsm_key_file(gsm_reference: str) -> Optional[str]:
    """Resolve a gsm:// reference to a temporary key file.

    Arguments:
        gsm_reference: Secret Manager reference (gsm://project/secret/version)

    Returns:
        Path to temporary file containing the key, or None if resolution failed.
    """
    try:
        from IAMSentry.helpers import hsecrets

        parsed = hsecrets.parse_gsm_reference(gsm_reference)
        if parsed is None:
            return None

        return hsecrets.get_secret_as_temp_file(
            parsed["project"], parsed["secret"], parsed["version"], suffix=".json"
        )
    except Exception as e:
        _log.error("Failed to resolve Secret Manager reference: %s", e)
        return None


def set_service_account(
    key_file_path: Optional[str] = None, scopes: Optional[List[str]] = None
) -> Credentials:
    """Get service account credentials (legacy function).

    Deprecated: Use get_credentials() instead for ADC support.

    Arguments:
        key_file_path: Path to service account key file.
        scopes: OAuth scopes (unused, kept for compatibility).

    Returns:
        Service account credentials.
    """
    if key_file_path is None:
        credentials, _ = get_credentials(scopes=scopes)
        return credentials

    return service_account.Credentials.from_service_account_file(key_file_path)


def get_service_account_class() -> type:
    """Return service account credentials class.

    Returns:
        service_account.Credentials class.
    """
    return service_account.Credentials


def build_resource(
    service_name: str,
    key_file_path: Optional[str] = None,
    version: str = "v1",
    timeout: int = API_TIMEOUT,
) -> discovery.Resource:
    """Create a Resource object for interacting with Google APIs.

    Supports both explicit key file and Application Default Credentials.

    Arguments:
        service_name: Name of the GCP service (e.g., 'cloudresourcemanager').
        key_file_path: Optional path to service account key file.
            If None, uses Application Default Credentials.
        version: API version (default: 'v1').
        timeout: Request timeout in seconds (default: 60).

    Returns:
        googleapiclient.discovery.Resource for API interactions.

    Example:
        >>> # Using ADC
        >>> crm = build_resource('cloudresourcemanager')
        >>>
        >>> # Using explicit key
        >>> crm = build_resource('cloudresourcemanager', '/path/to/key.json')
    """
    credentials, _ = get_credentials(key_file_path)

    # Build with custom http client for timeout support when available
    http = None
    if timeout:
        try:
            import httplib2

            http = httplib2.Http(timeout=timeout)
        except Exception:
            _log.warning(
                "httplib2 not installed; proceeding without custom timeout. "
                "Install with: pip install httplib2"
            )

    build_kwargs = {
        "credentials": credentials,
        "cache_discovery": False,
    }
    if http is not None:
        build_kwargs["http"] = http

    return discovery.build(service_name, version, **build_kwargs)


@retry_on_error()
def get_resource_iterator(resource: Any, key: Optional[str], **list_kwargs: Any) -> Iterator[Any]:
    """Generate resources for specific record types.

    This function handles pagination automatically when API returns
    pageToken for subsequent calls.

    Arguments:
        resource: GCP resource object with list() method.
        key: The key to look up in the GCP response JSON to find
            the list of resources. If None, yields the full response.
        **list_kwargs: Keyword arguments for resource.list() call.

    Yields:
        GCP configuration records.

    Example:
        >>> crm = build_resource('cloudresourcemanager')
        >>> for project in get_resource_iterator(crm.projects(), 'projects'):
        ...     print(project['projectId'])
    """
    try:
        request = resource.list(**list_kwargs)

        while request is not None:
            response = request.execute()
            if key is None:
                yield response
            else:
                for item in response.get(key, []):
                    yield item
            request = resource.list_next(previous_request=request, previous_response=response)
    except HttpError as e:
        _log.error(
            "Failed to fetch resource list; key: %s; list_kwargs: %s; error: %s: %s",
            key,
            list_kwargs,
            type(e).__name__,
            e,
        )
        raise
    except Exception as e:
        _log.error(
            "Unexpected error fetching resource list; key: %s; list_kwargs: %s; error: %s: %s",
            key,
            list_kwargs,
            type(e).__name__,
            e,
        )
        raise


def outline_gcp_project(
    project_index: int, project: dict, zone: Optional[str], key_file_path: Optional[str]
) -> str:
    """Return a summary of a GCP project for logging purpose.

    Arguments:
        project_index: Project index.
        project: GCP Resource object of the project.
        zone: Name of the zone for the project.
        key_file_path: Path of the service account key file for a project.

    Returns:
        String that can be used in log messages.
    """
    zone_log = "" if zone is None else f"zone: {zone}; "
    return (
        f"project #{project_index}: {project.get('projectId')} "
        f"({project.get('name')}) ({project.get('lifecycleState')}); "
        f"{zone_log}key_file_path: {key_file_path}"
    )
