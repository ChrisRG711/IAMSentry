"""Tests for IAMSentry configuration models."""

import pytest
from pydantic import ValidationError


class TestIAMSentryConfig:
    """Tests for the main IAMSentryConfig model."""

    def test_valid_config(self, sample_config_dict):
        """Test loading a valid configuration."""
        from IAMSentry.config_models import IAMSentryConfig

        config = IAMSentryConfig(**sample_config_dict)
        assert config.schedule == "02:00"
        assert "gcp_reader" in config.plugins
        assert "test_audit" in config.audits

    def test_minimal_config(self, minimal_config_dict):
        """Test minimal valid configuration."""
        from IAMSentry.config_models import IAMSentryConfig

        config = IAMSentryConfig(**minimal_config_dict)
        assert len(config.run) == 1

    def test_invalid_schedule_format(self, minimal_config_dict):
        """Test that invalid schedule format raises error."""
        from IAMSentry.config_models import IAMSentryConfig

        minimal_config_dict["schedule"] = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            IAMSentryConfig(**minimal_config_dict)
        assert "schedule" in str(exc_info.value)

    def test_invalid_schedule_time(self, minimal_config_dict):
        """Test that invalid time raises error."""
        from IAMSentry.config_models import IAMSentryConfig

        minimal_config_dict["schedule"] = "25:00"
        with pytest.raises(ValidationError) as exc_info:
            IAMSentryConfig(**minimal_config_dict)
        assert "schedule" in str(exc_info.value) or "Hours" in str(exc_info.value)

    def test_empty_run_list(self, minimal_config_dict):
        """Test that empty run list raises error."""
        from IAMSentry.config_models import IAMSentryConfig

        minimal_config_dict["run"] = []
        with pytest.raises(ValidationError) as exc_info:
            IAMSentryConfig(**minimal_config_dict)
        assert "run" in str(exc_info.value).lower()

    def test_undefined_audit_in_run(self, minimal_config_dict):
        """Test that referencing undefined audit raises error."""
        from IAMSentry.config_models import IAMSentryConfig

        minimal_config_dict["run"] = ["nonexistent_audit"]
        with pytest.raises(ValidationError) as exc_info:
            IAMSentryConfig(**minimal_config_dict)
        assert "nonexistent_audit" in str(exc_info.value)

    def test_undefined_plugin_in_audit(self, minimal_config_dict):
        """Test that referencing undefined plugin raises error."""
        from IAMSentry.config_models import IAMSentryConfig

        minimal_config_dict["audits"]["minimal"]["clouds"] = ["nonexistent_plugin"]
        with pytest.raises(ValidationError) as exc_info:
            IAMSentryConfig(**minimal_config_dict)
        assert "nonexistent_plugin" in str(exc_info.value)

    def test_from_yaml(self, sample_config_yaml):
        """Test loading from YAML file."""
        from IAMSentry.config_models import IAMSentryConfig

        config = IAMSentryConfig.from_yaml(str(sample_config_yaml))
        assert config.schedule == "02:00"

    def test_from_yaml_not_found(self):
        """Test loading from non-existent file."""
        from IAMSentry.config_models import IAMSentryConfig

        with pytest.raises(FileNotFoundError):
            IAMSentryConfig.from_yaml("/nonexistent/config.yaml")


class TestLoggerConfig:
    """Tests for LoggerConfig model."""

    def test_default_logger_config(self):
        """Test default logger configuration."""
        from IAMSentry.config_models import LoggerConfig

        config = LoggerConfig()
        assert config.version == 1
        assert config.disable_existing_loggers is False

    def test_custom_logger_config(self):
        """Test custom logger configuration."""
        from IAMSentry.config_models import LoggerConfig

        config = LoggerConfig(
            version=1,
            formatters={"simple": {"format": "%(message)s"}},
            handlers={"console": {"class": "logging.StreamHandler"}},
        )
        assert "simple" in config.formatters


class TestEmailConfig:
    """Tests for EmailConfig model."""

    def test_disabled_email(self):
        """Test disabled email requires no other fields."""
        from IAMSentry.config_models import EmailConfig

        config = EmailConfig(enabled=False)
        assert config.enabled is False

    def test_enabled_email_requires_fields(self):
        """Test enabled email requires smtp_server, from_email, to_emails."""
        from IAMSentry.config_models import EmailConfig

        with pytest.raises(ValidationError) as exc_info:
            EmailConfig(enabled=True)
        assert "smtp_server" in str(exc_info.value)

    def test_valid_enabled_email(self):
        """Test valid enabled email configuration."""
        from IAMSentry.config_models import EmailConfig

        config = EmailConfig(
            enabled=True,
            smtp_server="smtp.example.com",
            from_email="test@example.com",
            to_emails=["admin@example.com"],
        )
        assert config.enabled is True


class TestBasePluginConfig:
    """Tests for BasePluginConfig model."""

    def test_valid_plugin_name(self):
        """Test valid fully qualified plugin name."""
        from IAMSentry.config_models import BasePluginConfig

        config = BasePluginConfig(plugin="IAMSentry.plugins.gcp.gcpcloud.TestPlugin")
        assert config.plugin == "IAMSentry.plugins.gcp.gcpcloud.TestPlugin"

    def test_invalid_plugin_name(self):
        """Test invalid plugin name raises error."""
        from IAMSentry.config_models import BasePluginConfig

        with pytest.raises(ValidationError) as exc_info:
            BasePluginConfig(plugin="InvalidPlugin")
        assert "plugin" in str(exc_info.value).lower()


class TestGCPReaderPluginConfig:
    """Tests for GCPReaderPluginConfig model."""

    def test_valid_config(self):
        """Test valid GCP reader configuration."""
        from IAMSentry.config_models import GCPReaderPluginConfig

        config = GCPReaderPluginConfig(
            plugin="IAMSentry.plugins.gcp.gcpcloud.Reader",
            projects=["test-project"],
            regions=["global", "us-central1"],
        )
        assert config.projects == ["test-project"]

    def test_gsm_key_file_path(self):
        """Test gsm:// reference for key file."""
        from IAMSentry.config_models import GCPReaderPluginConfig

        config = GCPReaderPluginConfig(
            plugin="IAMSentry.plugins.gcp.gcpcloud.Reader",
            key_file_path="gsm://my-project/service-account-key",
        )
        assert config.key_file_path.startswith("gsm://")

    def test_string_project_normalized(self):
        """Test single project string is normalized to list."""
        from IAMSentry.config_models import GCPReaderPluginConfig

        config = GCPReaderPluginConfig(
            plugin="IAMSentry.plugins.gcp.gcpcloud.Reader", projects="single-project"
        )
        assert config.projects == ["single-project"]


class TestGCPProcessorPluginConfig:
    """Tests for GCPProcessorPluginConfig model."""

    def test_enforce_requires_enforcer(self):
        """Test that mode_enforce=True requires enforcer config."""
        from IAMSentry.config_models import GCPProcessorPluginConfig

        with pytest.raises(ValidationError) as exc_info:
            GCPProcessorPluginConfig(
                plugin="IAMSentry.plugins.gcp.gcpcloud.Processor", mode_enforce=True
            )
        assert "enforcer" in str(exc_info.value)

    def test_enforce_with_enforcer(self):
        """Test valid enforcement configuration."""
        from IAMSentry.config_models import EnforcerConfig, GCPProcessorPluginConfig

        config = GCPProcessorPluginConfig(
            plugin="IAMSentry.plugins.gcp.gcpcloud.Processor",
            mode_enforce=True,
            enforcer=EnforcerConfig(blocklist_projects=["production"]),
        )
        assert config.mode_enforce is True


class TestFileStorePluginConfig:
    """Tests for FileStorePluginConfig model."""

    def test_valid_json_format(self):
        """Test valid JSON file format."""
        from IAMSentry.config_models import FileStorePluginConfig

        config = FileStorePluginConfig(
            plugin="IAMSentry.plugins.files.filestore.FileStore", file_format="json"
        )
        assert config.file_format == "json"

    def test_valid_csv_format(self):
        """Test valid CSV file format."""
        from IAMSentry.config_models import FileStorePluginConfig

        config = FileStorePluginConfig(
            plugin="IAMSentry.plugins.files.filestore.FileStore", file_format="csv"
        )
        assert config.file_format == "csv"

    def test_invalid_format(self):
        """Test invalid file format raises error."""
        from IAMSentry.config_models import FileStorePluginConfig

        with pytest.raises(ValidationError) as exc_info:
            FileStorePluginConfig(
                plugin="IAMSentry.plugins.files.filestore.FileStore", file_format="xml"
            )
        assert "file_format" in str(exc_info.value)


class TestAuditConfig:
    """Tests for AuditConfig model."""

    def test_valid_audit(self):
        """Test valid audit configuration."""
        from IAMSentry.config_models import AuditConfig

        config = AuditConfig(clouds=["reader"], stores=["store"])
        assert len(config.clouds) == 1

    def test_empty_clouds(self):
        """Test empty clouds list raises error."""
        from IAMSentry.config_models import AuditConfig

        with pytest.raises(ValidationError):
            AuditConfig(clouds=[], stores=["store"])

    def test_empty_stores(self):
        """Test empty stores list raises error."""
        from IAMSentry.config_models import AuditConfig

        with pytest.raises(ValidationError):
            AuditConfig(clouds=["reader"], stores=[])


class TestValidateConfigFunction:
    """Tests for validate_config convenience function."""

    def test_validate_config(self, sample_config_yaml):
        """Test validate_config function."""
        from IAMSentry.config_models import validate_config

        config = validate_config(str(sample_config_yaml))
        assert config.schedule == "02:00"

    def test_validate_config_not_found(self):
        """Test validate_config with non-existent file."""
        from IAMSentry.config_models import validate_config

        with pytest.raises(FileNotFoundError):
            validate_config("/nonexistent/config.yaml")
