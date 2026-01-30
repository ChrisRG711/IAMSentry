"""Configuration models with Pydantic validation.

This module defines Pydantic models for validating IAMSentry configuration files.
All configuration is validated at load time, providing clear error messages
for invalid or missing settings.

Configuration Structure:
    The YAML configuration file has these main sections:
    - logger: Logging configuration (Python logging dictConfig format)
    - schedule: When to run scans (HH:MM format)
    - email: Optional email notification settings
    - plugins: Plugin definitions with their settings
    - audits: Audit workflows combining plugins
    - run: List of audits to execute

Example:
    >>> from IAMSentry.config_models import IAMSentryConfig
    >>> config = IAMSentryConfig.from_yaml('config.yaml')
    >>> print(config.schedule)
    '02:00'

    >>> # Validate a configuration file
    >>> from IAMSentry.config_models import validate_config
    >>> config = validate_config('config.yaml')
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = [
    "IAMSentryConfig",
    "validate_config",
    "LoggerConfig",
    "EmailConfig",
    "EnforcerConfig",
    "AuditConfig",
    "BasePluginConfig",
    "GCPReaderPluginConfig",
    "GCPProcessorPluginConfig",
    "FileStorePluginConfig",
]


class LoggerFormatterConfig(BaseModel):
    """Logging formatter configuration.

    Attributes:
        format: Log message format string using Python logging format codes.
        datefmt: Date/time format string.
    """
    format: str = '%(asctime)s %(levelname)s %(name)s - %(message)s'
    datefmt: Optional[str] = '%Y-%m-%d %H:%M:%S'


class LoggerHandlerConfig(BaseModel):
    """Logging handler configuration.

    Supports console, file, and rotating file handlers.

    Attributes:
        class_: Handler class name (e.g., 'logging.StreamHandler').
        formatter: Name of formatter to use.
        level: Logging level for this handler.
        stream: Stream for StreamHandler (e.g., 'ext://sys.stdout').
        filename: File path for FileHandler.
        when: Rotation interval for TimedRotatingFileHandler.
        encoding: File encoding.
        backupCount: Number of backup files to keep.
    """
    class_: str = Field(alias='class')
    formatter: Optional[str] = None
    level: Optional[str] = None
    stream: Optional[str] = None
    filename: Optional[str] = None
    when: Optional[str] = None
    encoding: Optional[str] = None
    backupCount: Optional[int] = None

    model_config = {'populate_by_name': True}


class LoggerRootConfig(BaseModel):
    """Root logger configuration.

    Attributes:
        level: Minimum logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        handlers: List of handler names to attach to root logger.
    """
    level: str = 'INFO'
    handlers: List[str] = Field(default_factory=lambda: ['console'])


class LoggerConfig(BaseModel):
    """Logging configuration section.

    Uses Python's logging.config.dictConfig format.

    Attributes:
        version: Config version (must be 1).
        disable_existing_loggers: Whether to disable existing loggers.
        formatters: Dictionary of formatter configurations.
        handlers: Dictionary of handler configurations.
        root: Root logger configuration.

    Example:
        logger:
          version: 1
          formatters:
            standard:
              format: '%(asctime)s %(levelname)s - %(message)s'
          handlers:
            console:
              class: logging.StreamHandler
              formatter: standard
          root:
            level: INFO
            handlers: [console]
    """
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Any] = Field(default_factory=dict)
    handlers: Dict[str, Any] = Field(default_factory=dict)
    root: Dict[str, Any] = Field(default_factory=dict)


class EmailConfig(BaseModel):
    """Email notification configuration.

    Sends email notifications for scan results and alerts.

    Attributes:
        enabled: Whether email notifications are enabled.
        smtp_server: SMTP server hostname.
        smtp_port: SMTP server port (default: 587 for TLS).
        from_email: Sender email address.
        to_emails: List of recipient email addresses.
        username: SMTP authentication username.
        password: SMTP authentication password.
        tls: Whether to use TLS encryption.

    Example:
        email:
          enabled: true
          smtp_server: smtp.gmail.com
          smtp_port: 587
          from_email: iamsentry@example.com
          to_emails:
            - security@example.com
          tls: true
    """
    enabled: bool = False
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    from_email: Optional[str] = None
    to_emails: List[str] = Field(default_factory=list)
    username: Optional[str] = None
    password: Optional[str] = None
    tls: bool = True

    @model_validator(mode='after')
    def validate_email_config(self):
        """Validate email config when enabled."""
        if self.enabled:
            if not self.smtp_server:
                raise ValueError('smtp_server required when email is enabled')
            if not self.from_email:
                raise ValueError('from_email required when email is enabled')
            if not self.to_emails:
                raise ValueError('to_emails required when email is enabled')
        return self


class EnforcerConfig(BaseModel):
    """IAM enforcement configuration.

    Controls which recommendations are automatically applied and
    safety thresholds to prevent accidental changes.

    Attributes:
        key_file_path: Service account key for making IAM changes.
        blocklist_projects: Projects to NEVER modify.
        blocklist_accounts: Accounts to NEVER modify.
        blocklist_account_types: Account types to NEVER modify.
        allowlist_projects: Only modify these projects (if set).
        allowlist_account_types: Only modify these account types.
        min_safe_to_apply_score_user: Minimum safety score for user accounts.
        min_safe_to_apply_score_group: Minimum safety score for groups.
        min_safe_to_apply_score_SA: Minimum safety score for service accounts.

    Example:
        enforcer:
          blocklist_projects:
            - production-critical
          blocklist_account_types:
            - serviceAccount
          min_safe_to_apply_score_user: 60
          min_safe_to_apply_score_SA: 80
    """
    key_file_path: Optional[str] = None
    blocklist_projects: List[str] = Field(
        default_factory=list,
        description="Projects to never modify"
    )
    blocklist_accounts: List[str] = Field(
        default_factory=list,
        description="Account IDs to never modify"
    )
    blocklist_account_types: List[str] = Field(
        default_factory=list,
        description="Account types to never modify (user, group, serviceAccount)"
    )
    allowlist_projects: List[str] = Field(
        default_factory=list,
        description="Only modify these projects (empty = all)"
    )
    allowlist_account_types: List[str] = Field(
        default_factory=list,
        description="Only modify these account types"
    )
    min_safe_to_apply_score_user: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimum safety score for user accounts (0-100)"
    )
    min_safe_to_apply_score_group: int = Field(
        default=40,
        ge=0,
        le=100,
        description="Minimum safety score for group accounts (0-100)"
    )
    min_safe_to_apply_score_SA: int = Field(
        default=80,
        ge=0,
        le=100,
        description="Minimum safety score for service accounts (0-100)"
    )


class BasePluginConfig(BaseModel):
    """Base configuration for all plugins.

    Attributes:
        plugin: Fully qualified plugin class name
            (e.g., 'IAMSentry.plugins.gcp.gcpcloud.GCPCloudIAMRecommendations').
    """
    plugin: str = Field(
        ...,
        description="Fully qualified plugin class name"
    )

    @field_validator('plugin')
    @classmethod
    def validate_plugin_name(cls, v: str) -> str:
        """Validate plugin name is fully qualified."""
        parts = v.split('.')
        if len(parts) < 3:
            raise ValueError(
                f"Invalid plugin name: {v}. "
                "Must be fully qualified (e.g., 'IAMSentry.plugins.gcp.gcpcloud.ClassName')"
            )
        return v

    model_config = {'extra': 'allow'}


class GCPReaderPluginConfig(BasePluginConfig):
    """GCP IAM Reader plugin configuration.

    Reads IAM recommendations from the GCP Recommender API.

    Attributes:
        key_file_path: Path to service account key file, or gsm:// reference.
            If None, uses Application Default Credentials.
        projects: List of project IDs to scan, or '*' for all accessible.
        regions: List of regions to scan (default: ['global']).
        processes: Number of parallel processes (1-32).
        threads: Number of threads per process (1-100).

    Example:
        gcp_reader:
          plugin: IAMSentry.plugins.gcp.gcpcloud.GCPCloudIAMRecommendations
          projects:
            - my-project-1
            - my-project-2
          processes: 4
          threads: 10
    """
    key_file_path: Optional[str] = Field(
        default=None,
        description="Service account key path or gsm:// reference"
    )
    projects: Union[str, List[str]] = Field(
        default_factory=list,
        description="Project IDs to scan, or '*' for all"
    )
    regions: List[str] = Field(
        default_factory=lambda: ['global'],
        description="Regions to scan"
    )
    processes: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of parallel processes"
    )
    threads: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Threads per process"
    )

    @field_validator('key_file_path')
    @classmethod
    def validate_key_file(cls, v: Optional[str]) -> Optional[str]:
        """Validate key file exists or is a gsm:// reference."""
        if v is None:
            return v
        # Allow gsm:// references
        if v.startswith('gsm://'):
            return v
        # Check file exists for local paths
        if not Path(v).exists():
            raise ValueError(f"Key file not found: {v}")
        return v

    @field_validator('projects', mode='before')
    @classmethod
    def normalize_projects(cls, v: Union[str, List[str]]) -> Union[str, List[str]]:
        """Normalize projects to list or wildcard."""
        if isinstance(v, str):
            return [v] if v != '*' else '*'
        return v


class GCPProcessorPluginConfig(BasePluginConfig):
    """GCP IAM Processor plugin configuration.

    Processes IAM recommendations and calculates risk scores.

    Attributes:
        mode_scan: Enable scan mode (read-only analysis).
        mode_enforce: Enable enforcement mode (apply changes).
        enforcer: Enforcement configuration (required if mode_enforce=True).

    Example:
        gcp_processor:
          plugin: IAMSentry.plugins.gcp.gcpcloudiam.GCPIAMRecommendationProcessor
          mode_scan: true
          mode_enforce: false
    """
    mode_scan: bool = Field(
        default=False,
        description="Enable scan mode (read-only)"
    )
    mode_enforce: bool = Field(
        default=False,
        description="Enable enforcement mode (applies changes)"
    )
    enforcer: Optional[EnforcerConfig] = Field(
        default=None,
        description="Enforcement settings (required if mode_enforce=True)"
    )

    @model_validator(mode='after')
    def validate_enforcer_required(self):
        """Validate enforcer config is present when enforcement is enabled."""
        if self.mode_enforce and not self.enforcer:
            raise ValueError(
                "enforcer configuration required when mode_enforce is True"
            )
        return self


class FileStorePluginConfig(BasePluginConfig):
    """File store plugin configuration.

    Saves scan results to JSON or CSV files.

    Attributes:
        output_dir: Directory for output files.
        file_format: Output format ('json' or 'csv').

    Example:
        file_store:
          plugin: IAMSentry.plugins.files.filestore.FileStore
          output_dir: ./output
          file_format: json
    """
    output_dir: str = Field(
        default='./output',
        description="Output directory for result files"
    )
    file_format: str = Field(
        default='json',
        description="Output format: json or csv"
    )

    @field_validator('file_format')
    @classmethod
    def validate_file_format(cls, v: str) -> str:
        """Validate file format is supported."""
        allowed = {'json', 'csv'}
        if v.lower() not in allowed:
            raise ValueError(f"file_format must be one of: {', '.join(allowed)}")
        return v.lower()


class AuditConfig(BaseModel):
    """Audit workflow configuration.

    Combines cloud plugins, processors, and storage to define
    a complete audit workflow.

    Attributes:
        clouds: List of cloud plugin names (data sources).
        processors: List of processor plugin names (analysis).
        stores: List of storage plugin names (output).
        alerts: List of alert plugin names (notifications).
        applyRecommendations: Whether to apply recommendations automatically.

    Example:
        audits:
          gcp_iam_audit:
            clouds:
              - gcp_reader
            processors:
              - gcp_processor
            stores:
              - file_store
    """
    clouds: List[str] = Field(
        ...,
        min_length=1,
        description="Cloud plugins to read from"
    )
    processors: List[str] = Field(
        default_factory=list,
        description="Processor plugins for analysis"
    )
    stores: List[str] = Field(
        ...,
        min_length=1,
        description="Storage plugins for output"
    )
    alerts: List[str] = Field(
        default_factory=list,
        description="Alert plugins for notifications"
    )
    applyRecommendations: bool = Field(
        default=False,
        description="Whether to automatically apply recommendations"
    )

    @model_validator(mode='after')
    def validate_apply_recommendations(self):
        """Warn about dangerous setting."""
        if self.applyRecommendations:
            import logging
            logging.getLogger(__name__).warning(
                "applyRecommendations is enabled! This will modify IAM policies."
            )
        return self


class IAMSentryConfig(BaseModel):
    """Root configuration model for IAMSentry.

    This is the main configuration class that validates the entire
    configuration file structure.

    Attributes:
        logger: Logging configuration.
        schedule: Time to run scans (HH:MM format).
        email: Email notification settings.
        plugins: Dictionary of plugin configurations.
        audits: Dictionary of audit configurations.
        run: List of audit names to execute.

    Example:
        >>> config = IAMSentryConfig.from_yaml('config.yaml')
        >>> print(f"Will run audits: {config.run}")
        >>> print(f"Scheduled for: {config.schedule}")
    """
    logger: LoggerConfig = Field(
        default_factory=LoggerConfig,
        description="Logging configuration"
    )
    schedule: str = Field(
        default="00:00",
        description="Time to run scans (HH:MM format)"
    )
    email: Optional[EmailConfig] = Field(
        default=None,
        description="Email notification settings"
    )
    plugins: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Plugin configurations"
    )
    audits: Dict[str, AuditConfig] = Field(
        default_factory=dict,
        description="Audit workflow definitions"
    )
    run: List[str] = Field(
        ...,
        min_length=1,
        description="List of audit names to execute"
    )

    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        """Validate schedule is in HH:MM format."""
        if not re.match(r'^\d{2}:\d{2}$', v):
            raise ValueError(
                f"Invalid schedule format: {v}. Must be HH:MM (e.g., '02:00')"
            )
        hours, minutes = map(int, v.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"Invalid time: {v}. Hours must be 0-23, minutes 0-59")
        return v

    @model_validator(mode='after')
    def validate_audit_references(self):
        """Validate that all referenced audits exist."""
        for audit_name in self.run:
            if audit_name not in self.audits:
                raise ValueError(
                    f"Audit '{audit_name}' referenced in 'run' but not defined in 'audits'"
                )
        return self

    @model_validator(mode='after')
    def validate_plugin_references(self):
        """Validate that all plugins referenced in audits exist."""
        for audit_name, audit in self.audits.items():
            for plugin_ref in audit.clouds + audit.processors + audit.stores + audit.alerts:
                if plugin_ref not in self.plugins:
                    raise ValueError(
                        f"Plugin '{plugin_ref}' referenced in audit '{audit_name}' "
                        "but not defined in 'plugins'"
                    )
        return self

    @classmethod
    def from_yaml(cls, filepath: str) -> 'IAMSentryConfig':
        """Load and validate configuration from YAML file.

        Arguments:
            filepath: Path to the YAML configuration file.

        Returns:
            Validated IAMSentryConfig instance.

        Raises:
            FileNotFoundError: If configuration file not found.
            ValidationError: If configuration is invalid.

        Example:
            >>> config = IAMSentryConfig.from_yaml('config.yaml')
        """
        import yaml
        from pathlib import Path

        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IAMSentryConfig':
        """Create configuration from dictionary.

        Arguments:
            data: Configuration dictionary.

        Returns:
            Validated IAMSentryConfig instance.

        Example:
            >>> config = IAMSentryConfig.from_dict({
            ...     'run': ['my_audit'],
            ...     'audits': {'my_audit': {...}},
            ...     'plugins': {...}
            ... })
        """
        return cls(**data)


def validate_config(filepath: str) -> IAMSentryConfig:
    """Validate a configuration file.

    Convenience function to validate a YAML configuration file.

    Arguments:
        filepath: Path to configuration file.

    Returns:
        Validated configuration.

    Raises:
        FileNotFoundError: If file not found.
        ValidationError: If configuration is invalid.

    Example:
        >>> config = validate_config('config.yaml')
        >>> print(f"Will run {len(config.run)} audits")
    """
    return IAMSentryConfig.from_yaml(filepath)
