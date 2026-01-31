"""Tests for IAMSentry helper modules."""

import logging
import tempfile
from pathlib import Path

import pytest
import yaml


class TestHLogging:
    """Tests for hlogging module."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a Logger instance."""
        from IAMSentry.helpers import hlogging

        logger = hlogging.get_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_get_logger_same_name_returns_same_logger(self):
        """Test that same name returns same logger instance."""
        from IAMSentry.helpers import hlogging

        logger1 = hlogging.get_logger("same_name")
        logger2 = hlogging.get_logger("same_name")
        assert logger1 is logger2

    def test_obfuscated_basic(self):
        """Test basic obfuscation."""
        from IAMSentry.helpers import hlogging

        result = hlogging.obfuscated("my-secret-value")
        assert result.startswith("my")
        assert result.endswith("ue")
        assert "*" in result
        assert len(result) == len("my-secret-value")

    def test_obfuscated_empty_string(self):
        """Test obfuscation of empty string."""
        from IAMSentry.helpers import hlogging

        assert hlogging.obfuscated("") == ""

    def test_obfuscated_short_string(self):
        """Test obfuscation of short string."""
        from IAMSentry.helpers import hlogging

        result = hlogging.obfuscated("ab")
        assert result == "**"

    def test_obfuscated_custom_visible_chars(self):
        """Test obfuscation with custom visible chars."""
        from IAMSentry.helpers import hlogging

        result = hlogging.obfuscated("my-secret-value", visible_chars=4)
        assert result.startswith("my-s")
        assert result.endswith("alue")


class TestHSecrets:
    """Tests for hsecrets module."""

    def test_parse_gsm_reference_valid(self):
        """Test parsing valid gsm:// reference."""
        from IAMSentry.helpers import hsecrets

        result = hsecrets.parse_gsm_reference("gsm://my-project/my-secret")
        assert result == {"project": "my-project", "secret": "my-secret", "version": "latest"}

    def test_parse_gsm_reference_with_version(self):
        """Test parsing gsm:// reference with version."""
        from IAMSentry.helpers import hsecrets

        result = hsecrets.parse_gsm_reference("gsm://my-project/my-secret/2")
        assert result == {"project": "my-project", "secret": "my-secret", "version": "2"}

    def test_parse_gsm_reference_invalid(self):
        """Test parsing invalid reference returns None."""
        from IAMSentry.helpers import hsecrets

        assert hsecrets.parse_gsm_reference("not-a-reference") is None
        assert hsecrets.parse_gsm_reference("http://example.com") is None
        assert hsecrets.parse_gsm_reference("") is None
        assert hsecrets.parse_gsm_reference(None) is None

    def test_is_gsm_reference(self):
        """Test is_gsm_reference function."""
        from IAMSentry.helpers import hsecrets

        assert hsecrets.is_gsm_reference("gsm://project/secret") is True
        assert hsecrets.is_gsm_reference("plain-value") is False
        assert hsecrets.is_gsm_reference(123) is False

    def test_resolve_secrets_plain_values(self):
        """Test resolve_secrets with no gsm:// references."""
        from IAMSentry.helpers import hsecrets

        config = {"host": "localhost", "port": 5432, "nested": {"value": "plain"}}
        result = hsecrets.resolve_secrets(config)
        assert result == config


class TestUtil:
    """Tests for util module."""

    def test_merge_dicts_basic(self):
        """Test basic dictionary merge."""
        from IAMSentry.helpers import util

        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = util.merge_dicts(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_dicts_empty_base(self):
        """Test merge with empty base."""
        from IAMSentry.helpers import util

        result = util.merge_dicts({}, {"a": 1})
        assert result == {"a": 1}

    def test_merge_dicts_empty_override(self):
        """Test merge with empty override."""
        from IAMSentry.helpers import util

        result = util.merge_dicts({"a": 1}, {})
        assert result == {"a": 1}

    def test_deep_merge_dicts(self):
        """Test deep dictionary merge."""
        from IAMSentry.helpers import util

        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 4, "z": 5}}
        result = util.deep_merge_dicts(base, override)

        assert result == {"a": {"x": 1, "y": 4, "z": 5}, "b": 3}

    def test_safe_get_exists(self):
        """Test safe_get with existing keys."""
        from IAMSentry.helpers import util

        data = {"a": {"b": {"c": 1}}}
        assert util.safe_get(data, "a", "b", "c") == 1

    def test_safe_get_missing(self):
        """Test safe_get with missing keys."""
        from IAMSentry.helpers import util

        data = {"a": {"b": 1}}
        assert util.safe_get(data, "a", "x", "y") is None
        assert util.safe_get(data, "a", "x", "y", default="default") == "default"

    def test_flatten_dict(self):
        """Test dictionary flattening."""
        from IAMSentry.helpers import util

        data = {"a": {"b": 1, "c": {"d": 2}}}
        result = util.flatten_dict(data)

        assert result == {"a.b": 1, "a.c.d": 2}

    def test_chunk_list(self):
        """Test list chunking."""
        from IAMSentry.helpers import util

        result = util.chunk_list([1, 2, 3, 4, 5], 2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_chunk_list_empty(self):
        """Test chunking empty list."""
        from IAMSentry.helpers import util

        result = util.chunk_list([], 2)
        assert result == []

    def test_filter_none(self):
        """Test filtering None values."""
        from IAMSentry.helpers import util

        data = {"a": 1, "b": None, "c": 3, "d": None}
        result = util.filter_none(data)

        assert result == {"a": 1, "c": 3}


class TestHCmd:
    """Tests for hcmd module."""

    def test_parse_default_config(self):
        """Test parsing with default config."""
        from IAMSentry.helpers import hcmd

        args = hcmd.parse([])
        assert args.config == "my_config.yaml"
        assert args.now is False
        assert args.print_base_config is False

    def test_parse_custom_config(self):
        """Test parsing with custom config."""
        from IAMSentry.helpers import hcmd

        args = hcmd.parse(["--config", "custom.yaml"])
        assert args.config == "custom.yaml"

    def test_parse_now_flag(self):
        """Test parsing --now flag."""
        from IAMSentry.helpers import hcmd

        args = hcmd.parse(["--now"])
        assert args.now is True

    def test_parse_short_flags(self):
        """Test parsing short flags."""
        from IAMSentry.helpers import hcmd

        args = hcmd.parse(["-c", "test.yaml", "-n"])
        assert args.config == "test.yaml"
        assert args.now is True


class TestHConfigs:
    """Tests for hconfigs module."""

    def test_config_load_valid(self, sample_config_yaml):
        """Test loading valid configuration."""
        from IAMSentry.helpers import hconfigs

        config = hconfigs.Config.load(sample_config_yaml)
        assert "plugins" in config
        assert "schedule" in config

    def test_config_getitem(self, sample_config_yaml):
        """Test config dictionary access."""
        from IAMSentry.helpers import hconfigs

        config = hconfigs.Config.load(sample_config_yaml)
        assert config["schedule"] == "02:00"

    def test_config_get_with_default(self, sample_config_yaml):
        """Test config.get with default."""
        from IAMSentry.helpers import hconfigs

        config = hconfigs.Config.load(sample_config_yaml)
        assert config.get("nonexistent", "default") == "default"

    def test_config_file_not_found(self):
        """Test loading non-existent file."""
        from IAMSentry.helpers import hconfigs

        with pytest.raises(FileNotFoundError):
            hconfigs.Config.load("/nonexistent/path/config.yaml")

    def test_config_keys(self, sample_config_yaml):
        """Test config.keys()."""
        from IAMSentry.helpers import hconfigs

        config = hconfigs.Config.load(sample_config_yaml)
        keys = list(config.keys())
        assert "plugins" in keys
        assert "schedule" in keys


class TestHEmails:
    """Tests for hemails module."""

    def test_send_without_config_logs(self):
        """Test send without config logs instead of sending."""
        from IAMSentry.helpers import hemails

        # Should return True when not configured (logs instead)
        result = hemails.send("Test content")
        assert result is True

    def test_send_dict_with_none_config(self):
        """Test send_dict with None config."""
        from IAMSentry.helpers import hemails

        result = hemails.send_dict(None, "Test content")
        assert result is True
