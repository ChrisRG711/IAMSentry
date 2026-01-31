"""Authentication middleware for IAMSentry Dashboard.

Provides multiple authentication methods for flexibility:
- API Key authentication for programmatic access
- HTTP Basic Auth for browser access
- Google IAP (Identity-Aware Proxy) for GCP-native deployments

No external dependencies or vendor lock-in (IAP validation uses google-auth).

Configuration via environment variables:
    IAMSENTRY_API_KEYS: Comma-separated list of valid API keys
    IAMSENTRY_BASIC_AUTH_USERS: Comma-separated user:password pairs
    IAMSENTRY_AUTH_ENABLED: Set to "false" to disable (default: true)

    # Google IAP settings (for Cloud Run/GKE behind IAP)
    IAMSENTRY_IAP_ENABLED: Set to "true" to enable IAP validation
    IAMSENTRY_IAP_AUDIENCE: Expected audience for IAP JWT (required if IAP enabled)
        Format: /projects/PROJECT_NUMBER/global/backendServices/SERVICE_ID
        Or: /projects/PROJECT_NUMBER/apps/PROJECT_ID (for App Engine)

Example:
    export IAMSENTRY_API_KEYS="key1,key2,key3"
    export IAMSENTRY_BASIC_AUTH_USERS="admin:secretpass,readonly:viewonly"
    export IAMSENTRY_AUTH_ENABLED="true"

    # For IAP:
    export IAMSENTRY_IAP_ENABLED="true"
    export IAMSENTRY_IAP_AUDIENCE="/projects/123456789/global/backendServices/987654321"

Usage in requests:
    # API Key via header
    curl -H "X-API-Key: your-api-key" http://localhost:8080/api/stats

    # Basic Auth
    curl -u admin:secretpass http://localhost:8080/api/stats

    # IAP (automatically handled by GCP - JWT passed in header)
    # X-Goog-IAP-JWT-Assertion header is validated automatically
"""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from IAMSentry.helpers import hlogging

_log = hlogging.get_logger(__name__)

__all__ = [
    "AuthConfig",
    "verify_authentication",
    "get_current_user",
    "require_auth",
    "verify_iap_jwt",
]


def verify_iap_jwt(iap_jwt: str, expected_audience: str) -> Optional[Dict]:
    """Verify a Google IAP JWT token.

    This validates the JWT assertion passed by Google Identity-Aware Proxy.
    When your app is deployed behind IAP, GCP automatically adds the
    X-Goog-IAP-JWT-Assertion header with a signed JWT.

    Arguments:
        iap_jwt: The JWT from X-Goog-IAP-JWT-Assertion header.
        expected_audience: The expected audience claim (your IAP client ID).
            Format: /projects/PROJECT_NUMBER/global/backendServices/SERVICE_ID

    Returns:
        Dict with user info (email, sub) if valid, None if invalid.

    Example:
        >>> jwt = request.headers.get("X-Goog-IAP-JWT-Assertion")
        >>> user = verify_iap_jwt(jwt, "/projects/123/global/backendServices/456")
        >>> if user:
        ...     print(f"Authenticated: {user['email']}")
    """
    if not iap_jwt or not expected_audience:
        return None

    try:
        from google.auth import jwt as google_jwt
        from google.auth.transport import requests as google_requests

        # IAP uses ES256 algorithm and Google's public keys
        # The google-auth library handles key fetching and caching
        decoded = google_jwt.decode(
            iap_jwt,
            certs_url="https://www.gstatic.com/iap/verify/public_key",
            audience=expected_audience,
        )

        # Extract user information
        email = decoded.get("email", "")
        subject = decoded.get("sub", "")

        if email:
            _log.debug("IAP authentication successful for: %s", email)
            return {
                "email": email,
                "sub": subject,
                "hd": decoded.get("hd", ""),  # Hosted domain (for G Suite)
                "iss": decoded.get("iss", ""),
            }

    except ImportError:
        _log.warning(
            "google-auth not installed, IAP verification unavailable. "
            "Install with: pip install google-auth"
        )
    except Exception as e:
        _log.warning("IAP JWT verification failed: %s", e)

    return None


class AuthConfig:
    """Authentication configuration loaded from environment.

    Attributes:
        enabled: Whether authentication is enabled.
        api_keys: Set of valid API keys.
        basic_auth_users: Dict mapping username to password hash.
        iap_enabled: Whether Google IAP validation is enabled.
        iap_audience: Expected audience for IAP JWT validation.
    """

    def __init__(self):
        """Load authentication configuration from environment."""
        self.enabled = os.environ.get("IAMSENTRY_AUTH_ENABLED", "true").lower() != "false"
        self.allow_default_key = (
            os.environ.get("IAMSENTRY_AUTH_ALLOW_DEFAULT_KEY", "false").lower() == "true"
        )
        self.log_default_key = (
            os.environ.get("IAMSENTRY_AUTH_LOG_DEFAULT_KEY", "false").lower() == "true"
        )

        # Google IAP configuration
        self.iap_enabled = os.environ.get("IAMSENTRY_IAP_ENABLED", "false").lower() == "true"
        self.iap_audience = os.environ.get("IAMSENTRY_IAP_AUDIENCE", "")

        if self.iap_enabled and not self.iap_audience:
            _log.warning(
                "IAP is enabled but IAMSENTRY_IAP_AUDIENCE is not set. "
                "IAP authentication will fail. Set the audience to your IAP client ID."
            )

        if self.iap_enabled:
            _log.info(
                "Google IAP authentication enabled with audience: %s",
                (
                    self.iap_audience[:50] + "..."
                    if len(self.iap_audience) > 50
                    else self.iap_audience
                ),
            )

        # Load API keys
        api_keys_str = os.environ.get("IAMSENTRY_API_KEYS", "")
        self.api_keys: set = set()
        if api_keys_str:
            self.api_keys = {k.strip() for k in api_keys_str.split(",") if k.strip()}

        # Load Basic Auth users (stored as username:password)
        basic_auth_str = os.environ.get("IAMSENTRY_BASIC_AUTH_USERS", "")
        self.basic_auth_users: Dict[str, str] = {}
        if basic_auth_str:
            for pair in basic_auth_str.split(","):
                if ":" in pair:
                    username, password = pair.split(":", 1)
                    # Store password hash, not plaintext
                    self.basic_auth_users[username.strip()] = self._hash_password(password.strip())

        # Generate a default key if none configured (for development)
        # Skip this if IAP is enabled (IAP handles auth)
        if (
            self.enabled
            and not self.api_keys
            and not self.basic_auth_users
            and not self.iap_enabled
        ):
            if self.allow_default_key:
                default_key = secrets.token_urlsafe(32)
                self.api_keys.add(default_key)
                if self.log_default_key:
                    _log.warning(
                        "No authentication configured! Generated temporary API key: %s", default_key
                    )
                else:
                    _log.warning(
                        "No authentication configured! Generated temporary API key (prefix): %s...",
                        default_key[:8],
                    )
                    _log.warning(
                        "Set IAMSENTRY_AUTH_LOG_DEFAULT_KEY=true to log the full key (dev only)."
                    )
                _log.warning(
                    "Set IAMSENTRY_API_KEYS or IAMSENTRY_BASIC_AUTH_USERS environment variables for production."
                )
            else:
                _log.error(
                    "Authentication is enabled but no credentials are configured. "
                    "Set IAMSENTRY_API_KEYS or IAMSENTRY_BASIC_AUTH_USERS."
                )

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password for secure comparison.

        Uses bcrypt via passlib for secure password hashing.
        Falls back to SHA-256 with warning if passlib is unavailable.
        """
        try:
            from passlib.context import CryptContext

            ctx = CryptContext(schemes=["bcrypt", "sha256_crypt"], deprecated="auto")
            return ctx.hash(password)
        except ImportError:
            _log.warning(
                "passlib not installed - using less secure SHA-256 hashing. "
                "Install passlib[bcrypt] for production: pip install 'passlib[bcrypt]'"
            )
            # Fallback with static salt - NOT recommended for production
            salt = "iamsentry_static_salt_v1"
            return hashlib.sha256((salt + password).encode()).hexdigest()

    def verify_api_key(self, api_key: str) -> bool:
        """Verify an API key.

        Arguments:
            api_key: The API key to verify.

        Returns:
            True if the API key is valid.
        """
        if not api_key:
            return False
        # Use constant-time comparison to prevent timing attacks
        return any(hmac.compare_digest(api_key, valid_key) for valid_key in self.api_keys)

    def verify_iap(self, iap_jwt: str) -> Optional[Dict]:
        """Verify a Google IAP JWT token.

        Arguments:
            iap_jwt: The JWT from X-Goog-IAP-JWT-Assertion header.

        Returns:
            Dict with user info if valid, None if invalid or IAP disabled.
        """
        if not self.iap_enabled or not self.iap_audience:
            return None

        return verify_iap_jwt(iap_jwt, self.iap_audience)

    def verify_basic_auth(self, username: str, password: str) -> bool:
        """Verify Basic Auth credentials.

        Arguments:
            username: The username.
            password: The password (plaintext, will be hashed for comparison).

        Returns:
            True if credentials are valid.
        """
        if not username or not password:
            return False

        stored_hash = self.basic_auth_users.get(username)
        if not stored_hash:
            return False

        # If stored hash looks like bcrypt/sha256_crypt, try passlib verify.
        if (
            stored_hash.startswith("$2")
            or stored_hash.startswith("$5$")
            or stored_hash.startswith("$6$")
        ):
            try:
                from passlib.context import CryptContext

                ctx = CryptContext(schemes=["bcrypt", "sha256_crypt"], deprecated="auto")
                return ctx.verify(password, stored_hash)
            except Exception:
                _log.warning(
                    "Passlib not available to verify hashed password for user: %s", username
                )
                return False

        password_hash = self._hash_password(password)
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(password_hash, stored_hash)


# Global auth config instance
_auth_config: Optional[AuthConfig] = None


def get_auth_config() -> AuthConfig:
    """Get the global authentication configuration.

    Returns:
        The AuthConfig instance.
    """
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig()
    return _auth_config


def reload_auth_config() -> AuthConfig:
    """Reload authentication configuration from environment.

    Useful for testing or dynamic config updates.

    Returns:
        The new AuthConfig instance.
    """
    global _auth_config
    _auth_config = AuthConfig()
    return _auth_config


# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
basic_auth = HTTPBasic(auto_error=False)


def _parse_basic_auth_header(auth_header: str) -> Optional[Tuple[str, str]]:
    """Parse a Basic Auth header.

    Arguments:
        auth_header: The Authorization header value.

    Returns:
        Tuple of (username, password) or None if invalid.
    """
    if not auth_header or not auth_header.startswith("Basic "):
        return None

    try:
        encoded = auth_header[6:]  # Remove "Basic " prefix
        decoded = base64.b64decode(encoded).decode("utf-8")
        if ":" not in decoded:
            return None
        username, password = decoded.split(":", 1)
        return (username, password)
    except Exception:
        return None


async def verify_authentication(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPBasicCredentials] = Security(basic_auth),
) -> Optional[str]:
    """Verify authentication from request.

    Checks for API key first, then falls back to Basic Auth.

    Arguments:
        request: The incoming request.
        api_key: API key from X-API-Key header (injected by FastAPI).
        credentials: Basic Auth credentials (injected by FastAPI).

    Returns:
        Username/identifier of authenticated user, or None if auth disabled.

    Raises:
        HTTPException: If authentication fails.
    """
    config = get_auth_config()

    # If auth is disabled, allow all requests
    if not config.enabled:
        return None

    # Try API Key first
    if api_key and config.verify_api_key(api_key):
        _log.debug("Authenticated via API key")
        # Use hash identifier instead of partial key to prevent targeted attacks
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:12]
        return f"api_key:{key_id}"

    # Try Basic Auth from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        parsed = _parse_basic_auth_header(auth_header)
        if parsed:
            username, password = parsed
            if config.verify_basic_auth(username, password):
                _log.debug("Authenticated via Basic Auth: %s", username)
                return f"user:{username}"

    # Try credentials from HTTPBasic security (backup)
    if credentials and config.verify_basic_auth(credentials.username, credentials.password):
        _log.debug("Authenticated via Basic Auth: %s", credentials.username)
        return f"user:{credentials.username}"

    # No valid authentication provided
    _log.warning(
        "Authentication failed for %s from %s",
        request.url.path,
        request.client.host if request.client else "unknown",
    )

    # Return 401 with WWW-Authenticate header for browser compatibility
    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": 'Basic realm="IAMSentry Dashboard"'},
    )


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPBasicCredentials] = Security(basic_auth),
) -> Optional[str]:
    """Get the current authenticated user.

    Same as verify_authentication, but exposed as a dependency.

    Arguments:
        request: The incoming request.
        api_key: API key from header.
        credentials: Basic Auth credentials.

    Returns:
        Username/identifier of authenticated user.
    """
    return await verify_authentication(request, api_key, credentials)


def require_auth(request: Request) -> str:
    """Dependency that requires authentication.

    Use this in route dependencies to enforce authentication.

    Arguments:
        request: The incoming request.

    Returns:
        Username/identifier of authenticated user.

    Raises:
        HTTPException: If not authenticated.
    """
    # This is a sync wrapper - the actual auth is done in middleware
    config = get_auth_config()
    if not config.enabled:
        return "anonymous"

    # Check if request has auth info attached by middleware
    user = getattr(request.state, "user", None)
    if user:
        return user

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": 'Basic realm="IAMSentry Dashboard"'},
    )


def generate_api_key() -> str:
    """Generate a new secure API key.

    Returns:
        A 32-byte URL-safe random string.
    """
    return secrets.token_urlsafe(32)


def create_auth_middleware(app):
    """Create authentication middleware for FastAPI app.

    This middleware runs before all requests and attaches
    user information to the request state.

    Arguments:
        app: The FastAPI application.

    Returns:
        The middleware function.
    """

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """Authentication middleware."""
        config = get_auth_config()

        # Skip auth for certain paths
        skip_paths = {"/", "/health", "/api/docs", "/api/redoc", "/openapi.json"}
        if request.url.path in skip_paths:
            return await call_next(request)

        # If auth is disabled, proceed
        if not config.enabled:
            request.state.user = "anonymous"
            return await call_next(request)

        # Try to authenticate
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization", "")

        user = None

        # Try API Key
        if api_key and config.verify_api_key(api_key):
            key_id = hashlib.sha256(api_key.encode()).hexdigest()[:12]
            user = f"api_key:{key_id}"

        # Try Basic Auth
        if not user and auth_header.startswith("Basic "):
            parsed = _parse_basic_auth_header(auth_header)
            if parsed:
                username, password = parsed
                if config.verify_basic_auth(username, password):
                    user = f"user:{username}"

        if user:
            request.state.user = user
            return await call_next(request)

        # Authentication failed
        _log.warning(
            "Unauthorized access attempt to %s from %s",
            request.url.path,
            request.client.host if request.client else "unknown",
        )

        return HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="IAMSentry Dashboard"'},
        )

    return auth_middleware
