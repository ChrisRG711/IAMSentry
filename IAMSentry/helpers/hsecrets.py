"""Google Secret Manager integration for IAMSentry.

This module provides secure credential retrieval from Google Secret Manager,
eliminating the need to store sensitive data in configuration files or
the repository.

Authentication:
    This module uses Application Default Credentials (ADC) to authenticate
    with Google Cloud. Ensure you have one of the following configured:

    1. Run 'gcloud auth application-default login' for local development
    2. Set GOOGLE_APPLICATION_CREDENTIALS environment variable
    3. Use workload identity on GKE
    4. Use the default service account on GCE/Cloud Run

Usage:
    >>> from IAMSentry.helpers import hsecrets
    >>>
    >>> # Get a secret value
    >>> api_key = hsecrets.get_secret('my-project', 'api-key')
    >>>
    >>> # Get a specific version
    >>> old_key = hsecrets.get_secret('my-project', 'api-key', version='1')
    >>>
    >>> # Resolve secrets in config using gsm:// syntax
    >>> config = {'password': 'gsm://my-project/db-password'}
    >>> resolved = hsecrets.resolve_secrets(config)
"""

import json
import logging
import os
import re
import tempfile
from typing import Any, Dict, Optional, Union

_log = logging.getLogger(__name__)

# Pattern to match Secret Manager references: gsm://project/secret or gsm://project/secret/version
GSM_PATTERN = re.compile(r'^gsm://([^/]+)/([^/]+)(?:/([^/]+))?$')

# Cache for secrets to avoid repeated API calls
_secret_cache: Dict[str, str] = {}

# Flag to track if Secret Manager client is available
_client = None
_client_initialized = False


def _get_client():
    """Get or initialize the Secret Manager client.

    Returns:
        SecretManagerServiceClient or None if unavailable.
    """
    global _client, _client_initialized

    if _client_initialized:
        return _client

    _client_initialized = True

    try:
        from google.cloud import secretmanager
        _client = secretmanager.SecretManagerServiceClient()
        _log.debug('Secret Manager client initialized successfully')
    except ImportError:
        _log.warning(
            'google-cloud-secret-manager not installed. '
            'Install with: pip install google-cloud-secret-manager'
        )
        _client = None
    except Exception as e:
        _log.warning('Failed to initialize Secret Manager client: %s', e)
        _client = None

    return _client


def get_secret(
    project_id: str,
    secret_id: str,
    version: str = 'latest',
    use_cache: bool = True
) -> Optional[str]:
    """Retrieve a secret value from Google Secret Manager.

    Arguments:
        project_id: GCP project ID containing the secret.
        secret_id: Name of the secret.
        version: Secret version (default: 'latest').
        use_cache: Whether to use cached values (default: True).

    Returns:
        The secret value as a string, or None if retrieval failed.

    Example:
        >>> password = get_secret('my-project', 'db-password')
        >>> api_key = get_secret('my-project', 'api-key', version='2')
    """
    cache_key = f'{project_id}/{secret_id}/{version}'

    if use_cache and cache_key in _secret_cache:
        _log.debug('Returning cached secret: %s/%s', project_id, secret_id)
        return _secret_cache[cache_key]

    client = _get_client()
    if client is None:
        _log.error('Secret Manager client not available')
        return None

    try:
        # Build the resource name
        name = f'projects/{project_id}/secrets/{secret_id}/versions/{version}'

        # Access the secret
        response = client.access_secret_version(request={'name': name})
        secret_value = response.payload.data.decode('UTF-8')

        # Cache the result
        if use_cache:
            _secret_cache[cache_key] = secret_value

        _log.debug('Retrieved secret: %s/%s (version: %s)', project_id, secret_id, version)
        return secret_value

    except Exception as e:
        _log.error(
            'Failed to retrieve secret %s/%s: %s: %s',
            project_id, secret_id, type(e).__name__, e
        )
        return None


def get_secret_as_json(
    project_id: str,
    secret_id: str,
    version: str = 'latest'
) -> Optional[Dict[str, Any]]:
    """Retrieve a secret and parse it as JSON.

    Useful for retrieving service account keys or other structured data.

    Arguments:
        project_id: GCP project ID containing the secret.
        secret_id: Name of the secret.
        version: Secret version (default: 'latest').

    Returns:
        Parsed JSON as a dictionary, or None if retrieval/parsing failed.

    Example:
        >>> sa_key = get_secret_as_json('my-project', 'service-account-key')
        >>> print(sa_key['client_email'])
    """
    secret_value = get_secret(project_id, secret_id, version)

    if secret_value is None:
        return None

    try:
        return json.loads(secret_value)
    except json.JSONDecodeError as e:
        _log.error('Failed to parse secret %s/%s as JSON: %s', project_id, secret_id, e)
        return None


def get_secret_as_temp_file(
    project_id: str,
    secret_id: str,
    version: str = 'latest',
    suffix: str = '.json'
) -> Optional[str]:
    """Retrieve a secret and write it to a temporary file.

    Useful for service account keys that need to be passed as file paths.
    The temporary file is created securely and the caller is responsible
    for cleanup.

    Arguments:
        project_id: GCP project ID containing the secret.
        secret_id: Name of the secret.
        version: Secret version (default: 'latest').
        suffix: File suffix (default: '.json').

    Returns:
        Path to the temporary file, or None if retrieval failed.

    Example:
        >>> key_path = get_secret_as_temp_file('my-project', 'sa-key')
        >>> # Use key_path with Google client libraries
        >>> os.unlink(key_path)  # Clean up when done
    """
    secret_value = get_secret(project_id, secret_id, version)

    if secret_value is None:
        return None

    try:
        # Create a secure temporary file
        fd, path = tempfile.mkstemp(suffix=suffix, prefix='iamsentry_secret_')
        os.write(fd, secret_value.encode('UTF-8'))
        os.close(fd)

        # Set restrictive permissions
        os.chmod(path, 0o600)

        _log.debug('Created temporary secret file: %s', path)
        return path

    except Exception as e:
        _log.error('Failed to create temporary file for secret: %s', e)
        return None


def parse_gsm_reference(value: str) -> Optional[Dict[str, str]]:
    """Parse a gsm:// reference string.

    Arguments:
        value: String potentially containing a gsm:// reference.

    Returns:
        Dictionary with 'project', 'secret', and 'version' keys,
        or None if the string is not a valid gsm:// reference.

    Example:
        >>> parse_gsm_reference('gsm://my-project/my-secret')
        {'project': 'my-project', 'secret': 'my-secret', 'version': 'latest'}
        >>> parse_gsm_reference('gsm://my-project/my-secret/2')
        {'project': 'my-project', 'secret': 'my-secret', 'version': '2'}
        >>> parse_gsm_reference('not-a-reference')
        None
    """
    if not isinstance(value, str):
        return None

    match = GSM_PATTERN.match(value)
    if not match:
        return None

    return {
        'project': match.group(1),
        'secret': match.group(2),
        'version': match.group(3) or 'latest'
    }


def resolve_secret_reference(value: str) -> str:
    """Resolve a gsm:// reference to its actual value.

    If the value is not a gsm:// reference, it is returned unchanged.

    Arguments:
        value: String potentially containing a gsm:// reference.

    Returns:
        The resolved secret value or the original value.

    Raises:
        ValueError: If the reference is valid but secret retrieval fails.
    """
    parsed = parse_gsm_reference(value)

    if parsed is None:
        return value

    secret_value = get_secret(
        parsed['project'],
        parsed['secret'],
        parsed['version']
    )

    if secret_value is None:
        raise ValueError(
            f"Failed to retrieve secret: {parsed['project']}/{parsed['secret']}"
        )

    return secret_value


def resolve_secrets(
    config: Dict[str, Any],
    recursive: bool = True
) -> Dict[str, Any]:
    """Resolve all gsm:// references in a configuration dictionary.

    Walks through the configuration and replaces any string values
    matching the gsm:// pattern with their actual secret values.

    Arguments:
        config: Configuration dictionary potentially containing gsm:// references.
        recursive: Whether to resolve nested dictionaries (default: True).

    Returns:
        New dictionary with all secrets resolved.

    Raises:
        ValueError: If any secret retrieval fails.

    Example:
        >>> config = {
        ...     'database': {
        ...         'host': 'localhost',
        ...         'password': 'gsm://my-project/db-password'
        ...     }
        ... }
        >>> resolved = resolve_secrets(config)
        >>> # resolved['database']['password'] now contains the actual password
    """
    result = {}

    for key, value in config.items():
        if isinstance(value, str):
            result[key] = resolve_secret_reference(value)
        elif isinstance(value, dict) and recursive:
            result[key] = resolve_secrets(value, recursive=True)
        elif isinstance(value, list):
            result[key] = [
                resolve_secret_reference(item) if isinstance(item, str)
                else resolve_secrets(item, recursive=True) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def clear_cache() -> None:
    """Clear the secret cache.

    Useful when secrets may have been rotated and you need fresh values.
    """
    global _secret_cache
    _secret_cache = {}
    _log.debug('Secret cache cleared')


def is_gsm_reference(value: Any) -> bool:
    """Check if a value is a gsm:// reference.

    Arguments:
        value: Value to check.

    Returns:
        True if the value is a gsm:// reference string.
    """
    return parse_gsm_reference(value) is not None


# Environment variable support
def get_secret_from_env(
    env_var: str,
    default_project: Optional[str] = None
) -> Optional[str]:
    """Get a secret referenced by an environment variable.

    The environment variable can contain either:
    - A gsm:// reference (e.g., gsm://project/secret)
    - A plain value (returned as-is)

    Arguments:
        env_var: Name of the environment variable.
        default_project: Default project ID if not specified in reference.

    Returns:
        The secret value or None if not found.

    Example:
        >>> # With DB_PASSWORD=gsm://my-project/db-pass
        >>> password = get_secret_from_env('DB_PASSWORD')
        >>>
        >>> # With API_KEY=actual-key-value
        >>> api_key = get_secret_from_env('API_KEY')
    """
    value = os.environ.get(env_var)

    if value is None:
        return None

    # Check if it's a gsm:// reference
    parsed = parse_gsm_reference(value)

    if parsed:
        return get_secret(parsed['project'], parsed['secret'], parsed['version'])

    # Check for shorthand: just secret name with default project
    if default_project and not value.startswith('gsm://') and '/' not in value:
        # Treat as secret name in default project
        return get_secret(default_project, value)

    # Return plain value
    return value
