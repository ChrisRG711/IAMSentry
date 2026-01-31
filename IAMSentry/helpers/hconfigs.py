"""Configuration loading utilities for IAMSentry.

This module provides configuration loading from YAML files with
support for base configuration merging, dictionary-like access,
and Google Secret Manager integration for secure credential handling.

Secret Manager Integration:
    Configuration values can reference secrets using the gsm:// syntax:
        key_file_path: gsm://project-id/secret-name
        password: gsm://project-id/db-password/latest

    Secrets are resolved when calling Config.load() with resolve_secrets=True
    or by calling config.resolve_secrets() after loading.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from IAMSentry import baseconfig

_log = logging.getLogger(__name__)


class Config:
    """Configuration container with YAML loading and dictionary-like access.

    This class loads configuration from YAML files and provides both
    dictionary-style access (config['key']) and method access (config.get('key')).

    The configuration is merged with the base configuration defined in
    IAMSentry.baseconfig, with user configuration taking precedence.

    Secret Manager Integration:
        Use gsm:// references in your config to securely load secrets:
            password: gsm://my-project/db-password

    Example:
        >>> from IAMSentry.helpers.hconfigs import Config
        >>> config = Config.load('my_config.yaml', resolve_secrets=True)
        >>> schedule = config['schedule']
        >>> email_config = config.get('email', None)
    """

    def __init__(self, data: Dict[str, Any], secrets_resolved: bool = False):
        """Initialize Config with a data dictionary.

        Arguments:
            data: Configuration dictionary.
            secrets_resolved: Whether secrets have been resolved.
        """
        self._data = data
        self._secrets_resolved = secrets_resolved

    def __getitem__(self, key: str) -> Any:
        """Get configuration value by key.

        Arguments:
            key: Configuration key.

        Returns:
            Configuration value.

        Raises:
            KeyError: If key not found in configuration.
        """
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in configuration.

        Arguments:
            key: Configuration key.

        Returns:
            True if key exists, False otherwise.
        """
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default.

        Arguments:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        return self._data.get(key, default)

    def keys(self):
        """Return configuration keys."""
        return self._data.keys()

    def items(self):
        """Return configuration items."""
        return self._data.items()

    def values(self):
        """Return configuration values."""
        return self._data.values()

    def resolve_secrets(self) -> 'Config':
        """Resolve all gsm:// secret references in the configuration.

        This method replaces all gsm:// references with their actual
        values from Google Secret Manager.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If any secret retrieval fails.

        Example:
            >>> config = Config.load('config.yaml')
            >>> config.resolve_secrets()  # Resolves all gsm:// references
        """
        if self._secrets_resolved:
            _log.debug('Secrets already resolved, skipping')
            return self

        try:
            from IAMSentry.helpers import hsecrets
            self._data = hsecrets.resolve_secrets(self._data)
            self._secrets_resolved = True
            _log.debug('Configuration secrets resolved successfully')
        except ImportError:
            _log.warning(
                'hsecrets module not available, gsm:// references will not be resolved'
            )
        except Exception as e:
            _log.error('Failed to resolve secrets: %s', e)
            raise

        return self

    @property
    def secrets_resolved(self) -> bool:
        """Check if secrets have been resolved."""
        return self._secrets_resolved

    @classmethod
    def load(
        cls,
        filepath: Union[str, Path],
        resolve_secrets: bool = False,
        validate: bool = True
    ) -> 'Config':
        """Load configuration from a YAML file.

        The user configuration is merged with the base configuration,
        with user values taking precedence.

        Arguments:
            filepath: Path to the YAML configuration file.
            resolve_secrets: Whether to resolve gsm:// secret references.
                If True, all gsm:// references will be replaced with their
                actual values from Google Secret Manager.

        Returns:
            Config instance with loaded configuration.

        Raises:
            FileNotFoundError: If configuration file not found.
            yaml.YAMLError: If YAML parsing fails.
            ValueError: If resolve_secrets=True and secret retrieval fails.

        Example:
            >>> # Load without resolving secrets (for inspection)
            >>> config = Config.load('config.yaml')
            >>>
            >>> # Load and resolve secrets in one step
            >>> config = Config.load('config.yaml', resolve_secrets=True)
        """
        # Allow legacy callers to pass a list/tuple of paths; use the first entry.
        if isinstance(filepath, (list, tuple)):
            if not filepath:
                raise FileNotFoundError("Configuration file list is empty")
            filepath = filepath[0]

        filepath = Path(filepath)

        # Check if file exists
        if not filepath.exists():
            # Try relative to current working directory
            cwd_path = Path.cwd() / filepath
            if cwd_path.exists():
                filepath = cwd_path
            else:
                raise FileNotFoundError(f"Configuration file not found: {filepath}")

        # Load user configuration
        with open(filepath, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f) or {}

        # Start with base configuration
        merged_config = _deep_merge(baseconfig.config_dict.copy(), user_config)

        # Optionally validate merged configuration with Pydantic models
        validate_env = os.environ.get("IAMSENTRY_VALIDATE_CONFIG", "true").lower() != "false"
        if validate and validate_env:
            try:
                from IAMSentry.config_models import IAMSentryConfig
                IAMSentryConfig.from_dict(merged_config)
            except Exception as e:
                _log.error("Configuration validation failed: %s", e)
                raise

        config = cls(merged_config)

        # Optionally resolve secrets
        if resolve_secrets:
            config.resolve_secrets()

        return config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries.

    Values from override take precedence. Nested dictionaries are
    merged recursively.

    Arguments:
        base: Base dictionary.
        override: Override dictionary (values take precedence).

    Returns:
        Merged dictionary.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


# Legacy function for backwards compatibility
def load(filepath: Union[str, Path]) -> Config:
    """Load configuration from file.

    This is a convenience function that calls Config.load().

    Arguments:
        filepath: Path to configuration file.

    Returns:
        Config instance.
    """
    return Config.load(filepath)
