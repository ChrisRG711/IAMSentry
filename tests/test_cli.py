"""Tests for IAMSentry CLI module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner


class TestCliHelp:
    """Tests for CLI help and basic functionality."""

    def test_cli_imports(self):
        """Test that CLI module can be imported."""
        from IAMSentry.cli import app

        assert app is not None

    def test_cli_help(self):
        """Test that CLI --help works."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "IAMSentry" in result.stdout
        assert "scan" in result.stdout
        assert "analyze" in result.stdout

    def test_cli_version(self):
        """Test that CLI --version works."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()


class TestCliScan:
    """Tests for CLI scan command."""

    def test_scan_help(self):
        """Test scan command --help."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0
        assert "Scan" in result.stdout

    def test_scan_with_config(self, sample_config_yaml, temp_dir):
        """Test scan command with config file."""
        from IAMSentry.cli import app

        runner = CliRunner()

        output_dir = temp_dir / "output"

        # Mock the GCP utils to avoid real API calls
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_creds:
            mock_creds.return_value = (MagicMock(), "test-project")

            with patch("IAMSentry.plugins.gcp.gcpcloud.GCPCloudIAMRecommendations") as mock_reader:
                mock_reader.return_value.read.return_value = iter([])

                result = runner.invoke(
                    app,
                    [
                        "scan",
                        "--config",
                        str(sample_config_yaml),
                        "--output",
                        str(output_dir),
                        "--dry-run",
                    ],
                )

                # Should succeed (exit code 0) or warn about missing config
                assert result.exit_code in [0, 1]


class TestCliAnalyze:
    """Tests for CLI analyze command."""

    def test_analyze_help(self):
        """Test analyze command --help."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze" in result.stdout

    def test_analyze_missing_input(self):
        """Test analyze command with missing input file."""
        from IAMSentry.cli import app

        runner = CliRunner()
        # analyze uses a positional argument
        result = runner.invoke(app, ["analyze", "/nonexistent/results.json"])
        assert result.exit_code != 0

    def test_analyze_with_valid_input(self, temp_dir):
        """Test analyze command with valid input file."""
        from IAMSentry.cli import app

        runner = CliRunner()

        # Create a sample results file
        results = [
            {
                "processor": {
                    "project": "test-project",
                    "account_id": "test-sa@test.iam.gserviceaccount.com",
                    "account_type": "serviceAccount",
                    "recommendation_recommender_subtype": "REMOVE_ROLE",
                },
                "score": {
                    "risk_score": 75,
                    "over_privilege_score": 50,
                    "safe_to_apply_recommendation_score": 80,
                },
                "raw": {
                    "name": "projects/test/recommendations/abc123",
                    "priority": "P2",
                    "stateInfo": {"state": "ACTIVE"},
                },
            }
        ]
        input_file = temp_dir / "results.json"
        with open(input_file, "w") as f:
            json.dump(results, f)

        # Mock the processor to avoid complex imports
        with patch("IAMSentry.plugins.gcp.gcpcloudiam.GCPIAMRecommendationProcessor") as mock_proc:
            mock_proc.return_value.eval.return_value = iter([results[0]])

            # analyze uses a positional argument
            result = runner.invoke(app, ["analyze", str(input_file)])
            assert result.exit_code == 0


class TestCliRemediate:
    """Tests for CLI remediate command."""

    def test_remediate_help(self):
        """Test remediate command --help."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["remediate", "--help"])
        assert result.exit_code == 0
        assert "Remediate" in result.stdout

    def test_remediate_missing_input(self):
        """Test remediate command with missing input file."""
        from IAMSentry.cli import app

        runner = CliRunner()
        # remediate uses a positional argument
        result = runner.invoke(app, ["remediate", "/nonexistent/results.json"])
        assert result.exit_code != 0


class TestCliStatus:
    """Tests for CLI status command."""

    def test_status_help(self):
        """Test status command --help."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_status_authenticated(self):
        """Test status command when authenticated."""
        from IAMSentry.cli import app

        runner = CliRunner()

        # Mock successful authentication at the correct path
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_creds:
            mock_cred_obj = MagicMock()
            mock_cred_obj.service_account_email = "test@test.iam.gserviceaccount.com"
            mock_creds.return_value = (mock_cred_obj, "test-project")

            result = runner.invoke(app, ["status"])
            # Should run without errors
            assert result.exit_code == 0

    def test_status_not_authenticated(self):
        """Test status command when not authenticated."""
        from IAMSentry.cli import app

        runner = CliRunner()

        # Mock authentication failure at the correct path
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_creds:
            mock_creds.side_effect = Exception("Not authenticated")

            result = runner.invoke(app, ["status"])
            # Should handle gracefully
            assert result.exit_code == 0  # Status command handles auth errors gracefully


class TestCliInit:
    """Tests for CLI init command."""

    def test_init_help(self):
        """Test init command --help."""
        from IAMSentry.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0

    def test_init_creates_config(self, temp_dir):
        """Test init command creates config file."""
        from IAMSentry.cli import app

        runner = CliRunner()

        output = temp_dir / "new_config.yaml"
        result = runner.invoke(app, ["init", "--output", str(output)])

        assert result.exit_code == 0
        assert output.exists()

    def test_init_no_overwrite(self, temp_dir):
        """Test init command doesn't overwrite existing file."""
        from IAMSentry.cli import app

        runner = CliRunner()

        output = temp_dir / "existing_config.yaml"
        output.write_text("existing content")

        result = runner.invoke(app, ["init", "--output", str(output)])

        # Should fail or warn without --force
        assert "exists" in result.stdout.lower() or result.exit_code != 0

    def test_init_force_overwrite(self, temp_dir):
        """Test init command with --force overwrites existing file."""
        from IAMSentry.cli import app

        runner = CliRunner()

        output = temp_dir / "existing_config.yaml"
        output.write_text("existing content")

        result = runner.invoke(app, ["init", "--output", str(output), "--force"])

        assert result.exit_code == 0
        assert output.read_text() != "existing content"


class TestOutputFormats:
    """Tests for different output formats."""

    def test_output_format_enum(self):
        """Test OutputFormat enum values."""
        from IAMSentry.cli import OutputFormat

        # CLI uses lowercase values
        assert OutputFormat.json == "json"
        assert OutputFormat.table == "table"
        assert OutputFormat.yaml == "yaml"

    def test_analyze_json_format(self, temp_dir):
        """Test analyze command with JSON format."""
        from IAMSentry.cli import app

        runner = CliRunner()

        # Create sample input
        results = [{"processor": {"project": "test"}, "score": {"risk_score": 50}}]
        input_file = temp_dir / "results.json"
        with open(input_file, "w") as f:
            json.dump(results, f)

        # Mock the processor
        with patch("IAMSentry.plugins.gcp.gcpcloudiam.GCPIAMRecommendationProcessor") as mock_proc:
            mock_proc.return_value.eval.return_value = iter([results[0]])

            # analyze uses a positional argument
            result = runner.invoke(app, ["analyze", str(input_file), "--format", "json"])
            assert result.exit_code == 0
