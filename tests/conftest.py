"""Pytest configuration and fixtures for IAMSentry tests."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict() -> Dict[str, Any]:
    """Return a valid sample configuration dictionary."""
    return {
        "logger": {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(message)s"}},
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
            "root": {"level": "INFO", "handlers": ["console"]},
        },
        "schedule": "02:00",
        "plugins": {
            "gcp_reader": {
                "plugin": "IAMSentry.plugins.gcp.gcpcloud.GCPCloudIAMRecommendations",
                "projects": ["test-project"],
                "regions": ["global"],
            },
            "gcp_processor": {
                "plugin": "IAMSentry.plugins.gcp.gcpcloudiam.GCPIAMRecommendationProcessor",
                "mode_scan": True,
                "mode_enforce": False,
            },
            "file_store": {
                "plugin": "IAMSentry.plugins.files.filestore.FileStore",
                "output_dir": "./output",
                "file_format": "json",
            },
        },
        "audits": {
            "test_audit": {
                "clouds": ["gcp_reader"],
                "processors": ["gcp_processor"],
                "stores": ["file_store"],
                "alerts": [],
            }
        },
        "run": ["test_audit"],
    }


@pytest.fixture
def sample_config_yaml(temp_dir, sample_config_dict) -> Path:
    """Create a sample YAML configuration file."""
    config_path = temp_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config_dict, f)
    return config_path


@pytest.fixture
def minimal_config_dict() -> Dict[str, Any]:
    """Return a minimal valid configuration dictionary."""
    return {
        "plugins": {
            "reader": {"plugin": "IAMSentry.plugins.test.reader.TestReader"},
            "store": {"plugin": "IAMSentry.plugins.test.store.TestStore"},
        },
        "audits": {"minimal": {"clouds": ["reader"], "stores": ["store"]}},
        "run": ["minimal"],
    }


@pytest.fixture
def invalid_config_dict() -> Dict[str, Any]:
    """Return an invalid configuration dictionary."""
    return {
        "schedule": "invalid",  # Invalid format
        "plugins": {},
        "audits": {},
        "run": [],  # Empty run list
    }


@pytest.fixture
def mock_env_vars():
    """Context manager to temporarily set environment variables."""
    original = os.environ.copy()

    def _set_vars(**kwargs):
        for key, value in kwargs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    yield _set_vars

    # Restore original environment
    os.environ.clear()
    os.environ.update(original)
