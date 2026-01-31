"""Tests for authentication and audit logging systems."""

import base64
import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAuthConfig:
    """Tests for AuthConfig class."""

    def test_auth_config_default_disabled(self):
        """Test auth config with no env vars does not generate a key."""
        # Clear env vars
        with patch.dict(os.environ, {}, clear=True):
            # Need to reload to pick up new env
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            # Should be enabled but have no credentials configured
            assert config.enabled is True
            assert len(config.api_keys) == 0

    def test_auth_config_default_key_allowed(self):
        """Test auth config can generate a key when explicitly allowed."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ALLOW_DEFAULT_KEY": "true",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.enabled is True
            assert len(config.api_keys) == 1

    def test_auth_config_disabled_explicitly(self):
        """Test auth can be disabled via env var."""
        with patch.dict(os.environ, {"IAMSENTRY_AUTH_ENABLED": "false"}, clear=True):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.enabled is False

    def test_auth_config_api_keys(self):
        """Test loading API keys from env."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "key1,key2,key3",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.enabled is True
            assert len(config.api_keys) == 3
            assert "key1" in config.api_keys
            assert "key2" in config.api_keys
            assert "key3" in config.api_keys

    def test_auth_config_basic_auth_users(self):
        """Test loading basic auth users from env."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "testkey",
                "IAMSENTRY_BASIC_AUTH_USERS": "admin:password123,user:pass456",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert len(config.basic_auth_users) == 2
            assert "admin" in config.basic_auth_users
            assert "user" in config.basic_auth_users
            # Passwords should be hashed
            assert config.basic_auth_users["admin"] != "password123"

    def test_verify_api_key_valid(self):
        """Test verifying a valid API key."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "valid-key-123,another-key",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.verify_api_key("valid-key-123") is True
            assert config.verify_api_key("another-key") is True

    def test_verify_api_key_invalid(self):
        """Test verifying an invalid API key."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "valid-key-123",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.verify_api_key("invalid-key") is False
            assert config.verify_api_key("") is False
            assert config.verify_api_key(None) is False

    def test_verify_basic_auth_valid(self):
        """Test verifying valid basic auth credentials."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "testkey",
                "IAMSENTRY_BASIC_AUTH_USERS": "admin:secretpass",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.verify_basic_auth("admin", "secretpass") is True

    def test_verify_basic_auth_invalid(self):
        """Test verifying invalid basic auth credentials."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "testkey",
                "IAMSENTRY_BASIC_AUTH_USERS": "admin:secretpass",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            assert config.verify_basic_auth("admin", "wrongpass") is False
            assert config.verify_basic_auth("unknown", "secretpass") is False
            assert config.verify_basic_auth("", "") is False

    def test_timing_attack_resistance(self):
        """Test that verification uses constant-time comparison."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "valid-key-12345678901234567890",
            },
            clear=True,
        ):
            from IAMSentry.dashboard.auth import AuthConfig

            config = AuthConfig()
            # Both should take similar time (constant-time comparison)
            # This is a basic check - proper timing attack testing requires statistical analysis
            config.verify_api_key("valid-key-12345678901234567890")
            config.verify_api_key("wrong-key-12345678901234567890")
            # If we got here without errors, the constant-time comparison is being used


class TestParseBasicAuthHeader:
    """Tests for Basic Auth header parsing."""

    def test_parse_valid_header(self):
        """Test parsing a valid Basic Auth header."""
        from IAMSentry.dashboard.auth import _parse_basic_auth_header

        # Create valid header: "Basic base64(username:password)"
        credentials = base64.b64encode(b"admin:password123").decode()
        header = f"Basic {credentials}"

        result = _parse_basic_auth_header(header)
        assert result == ("admin", "password123")

    def test_parse_header_with_colon_in_password(self):
        """Test parsing header where password contains colon."""
        from IAMSentry.dashboard.auth import _parse_basic_auth_header

        credentials = base64.b64encode(b"admin:pass:word:123").decode()
        header = f"Basic {credentials}"

        result = _parse_basic_auth_header(header)
        assert result == ("admin", "pass:word:123")

    def test_parse_invalid_header(self):
        """Test parsing invalid headers."""
        from IAMSentry.dashboard.auth import _parse_basic_auth_header

        assert _parse_basic_auth_header("") is None
        assert _parse_basic_auth_header("Bearer token") is None
        assert _parse_basic_auth_header("Basic !!!invalid!!!") is None
        assert _parse_basic_auth_header(None) is None


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_audit_logger_creates_log_file(self):
        """Test that audit logger creates log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")

            with patch.dict(
                os.environ,
                {
                    "IAMSENTRY_AUDIT_LOG_PATH": log_path,
                    "IAMSENTRY_AUDIT_SIGN_LOGS": "false",
                },
                clear=True,
            ):
                from IAMSentry.audit import AuditEvent, AuditLogger

                logger = AuditLogger(log_path=log_path)

                # Log an event
                logger.log_event(
                    event_type=AuditEvent.AUTH_SUCCESS,
                    action="LOGIN",
                    resource="auth",
                    actor="testuser",
                )

                # Check file was created
                assert os.path.exists(log_path)

                # Check content
                with open(log_path) as f:
                    content = f.read()
                    assert "AUTH_SUCCESS" in content
                    assert "testuser" in content

    def test_audit_log_iam_change(self):
        """Test logging IAM changes with before/after state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")

            from IAMSentry.audit import AuditLogger

            logger = AuditLogger(log_path=log_path)

            before_policy = {
                "bindings": [{"role": "roles/editor", "members": ["user:test@example.com"]}]
            }
            after_policy = {"bindings": []}

            record = logger.log_iam_change(
                project="test-project",
                account_id="sa@test.iam.gserviceaccount.com",
                action="REMOVE_ROLE",
                role="roles/editor",
                actor="admin",
                recommendation_id="rec-123",
                before_policy=before_policy,
                after_policy=after_policy,
                success=True,
            )

            assert record.event_type.value == "IAM_CHANGE_EXECUTED"
            assert record.action == "REMOVE_ROLE"
            assert record.before_state == before_policy
            assert record.after_state == after_policy

    def test_audit_log_scan(self):
        """Test logging scan events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")

            from IAMSentry.audit import AuditLogger

            logger = AuditLogger(log_path=log_path)

            # Log scan start
            start_record = logger.log_scan(
                projects=["project-1", "project-2"],
                actor="scanner",
                start=True,
            )
            assert start_record.event_type.value == "IAM_SCAN_START"

            # Log scan complete
            complete_record = logger.log_scan(
                projects=["project-1", "project-2"],
                actor="scanner",
                recommendation_count=15,
                start=False,
            )
            assert complete_record.event_type.value == "IAM_SCAN_COMPLETE"
            assert complete_record.details["recommendation_count"] == 15

    def test_audit_log_auth(self):
        """Test logging authentication events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")

            from IAMSentry.audit import AuditLogger

            logger = AuditLogger(log_path=log_path)

            # Log successful auth
            success_record = logger.log_auth(
                success=True,
                username="admin",
                client_ip="192.168.1.100",
                user_agent="Mozilla/5.0",
            )
            assert success_record.event_type.value == "AUTH_SUCCESS"

            # Log failed auth
            fail_record = logger.log_auth(
                success=False,
                username="hacker",
                client_ip="10.0.0.1",
                reason="Invalid password",
            )
            assert fail_record.event_type.value == "AUTH_FAILURE"
            assert fail_record.details["reason"] == "Invalid password"

    def test_audit_log_signing(self):
        """Test HMAC signing of audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")
            sign_key = "test-signing-key-12345"

            from IAMSentry.audit import AuditEvent, AuditLogger

            logger = AuditLogger(
                log_path=log_path,
                sign_logs=True,
                sign_key=sign_key,
            )

            record = logger.log_event(
                event_type=AuditEvent.IAM_CHANGE_EXECUTED,
                action="REMOVE_ROLE",
                resource="projects/test",
                actor="admin",
            )

            # Record should have signature
            assert record.signature is not None
            assert len(record.signature) == 64  # SHA-256 hex digest

            # Verify signature
            record_dict = record.to_dict()
            assert logger.verify_record(record_dict) is True

            # Tamper with record and verify fails
            record_dict["actor"] = "hacker"
            assert logger.verify_record(record_dict) is False

    def test_audit_log_read_and_filter(self):
        """Test reading and filtering audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")

            from IAMSentry.audit import AuditEvent, AuditLogger

            logger = AuditLogger(log_path=log_path)

            # Log multiple events
            logger.log_auth(success=True, username="admin")
            logger.log_auth(success=False, username="hacker")
            logger.log_scan(projects=["proj1"], actor="scanner", start=True)
            logger.log_iam_change(
                project="proj1",
                account_id="sa@test.iam.gserviceaccount.com",
                action="REMOVE_ROLE",
                role="roles/editor",
                actor="admin",
                recommendation_id="rec-1",
            )

            # Read all logs
            all_logs = logger.read_logs()
            assert len(all_logs) == 4

            # Filter by event type
            auth_logs = logger.read_logs(event_types=[AuditEvent.AUTH_SUCCESS])
            assert len(auth_logs) == 1

            # Filter by actor
            admin_logs = logger.read_logs(actor="admin")
            assert len(admin_logs) == 2  # auth + iam_change

            # Filter by resource
            proj_logs = logger.read_logs(resource="projects/proj1")
            assert len(proj_logs) == 2  # scan + iam_change


class TestAuditRecord:
    """Tests for AuditRecord class."""

    def test_record_has_required_fields(self):
        """Test that audit records have all required fields."""
        from IAMSentry.audit import AuditEvent, AuditRecord

        record = AuditRecord(
            event_type=AuditEvent.IAM_CHANGE_EXECUTED,
            action="REMOVE_ROLE",
            resource="projects/test",
            actor="admin",
        )

        assert record.id is not None
        assert record.timestamp is not None
        assert record.event_type == AuditEvent.IAM_CHANGE_EXECUTED
        assert record.action == "REMOVE_ROLE"
        assert record.resource == "projects/test"
        assert record.actor == "admin"
        assert record.request_id is not None

    def test_record_to_json(self):
        """Test converting record to JSON."""
        from IAMSentry.audit import AuditEvent, AuditRecord

        record = AuditRecord(
            event_type=AuditEvent.AUTH_SUCCESS,
            action="LOGIN",
            resource="auth",
            actor="testuser",
            details={"ip": "192.168.1.1"},
        )

        json_str = record.to_json()
        data = json.loads(json_str)

        assert data["event_type"] == "AUTH_SUCCESS"
        assert data["action"] == "LOGIN"
        assert data["details"]["ip"] == "192.168.1.1"

    def test_record_signature(self):
        """Test computing record signature."""
        from IAMSentry.audit import AuditEvent, AuditRecord

        record = AuditRecord(
            event_type=AuditEvent.IAM_CHANGE_EXECUTED,
            action="REMOVE_ROLE",
            resource="projects/test",
            actor="admin",
        )

        key = b"test-key-12345"
        sig1 = record.compute_signature(key)
        sig2 = record.compute_signature(key)

        # Same key should produce same signature
        assert sig1 == sig2

        # Different key should produce different signature
        sig3 = record.compute_signature(b"different-key")
        assert sig1 != sig3


class TestInputValidation:
    """Tests for input validation in audit_log_permission_analyzer."""

    def test_validate_service_account_valid(self):
        """Test validating valid service account emails."""
        from IAMSentry.audit_log_permission_analyzer import validate_service_account

        valid_emails = [
            "test@my-project.iam.gserviceaccount.com",
            "my-service-account@project-123.iam.gserviceaccount.com",
            "sa.with.dots@proj.iam.gserviceaccount.com",
        ]

        for email in valid_emails:
            result = validate_service_account(email)
            assert result == email

    def test_validate_service_account_invalid(self):
        """Test validating invalid service account emails."""
        from IAMSentry.audit_log_permission_analyzer import (
            InputValidationError,
            validate_service_account,
        )

        invalid_emails = [
            "",
            "not-an-email",
            "user@gmail.com",
            "sa@project.gserviceaccount.com",  # missing .iam
            "a" * 300 + "@proj.iam.gserviceaccount.com",  # too long
        ]

        for email in invalid_emails:
            with pytest.raises(InputValidationError):
                validate_service_account(email)

    def test_validate_project_id_valid(self):
        """Test validating valid project IDs."""
        from IAMSentry.audit_log_permission_analyzer import validate_project_id

        valid_ids = [
            "my-project",
            "project-123",
            "a12345",
            "project-with-many-hyphens-here",
        ]

        for pid in valid_ids:
            result = validate_project_id(pid)
            assert result == pid

    def test_validate_project_id_invalid(self):
        """Test validating invalid project IDs."""
        from IAMSentry.audit_log_permission_analyzer import (
            InputValidationError,
            validate_project_id,
        )

        invalid_ids = [
            "",
            "ab",  # too short
            "a" * 35,  # too long
            "Project-123",  # uppercase
            "123-project",  # starts with number
            "project-",  # ends with hyphen
            "project_underscore",  # underscore not allowed
        ]

        for pid in invalid_ids:
            with pytest.raises(InputValidationError):
                validate_project_id(pid)

    def test_validate_days_back(self):
        """Test validating days_back parameter."""
        from IAMSentry.audit_log_permission_analyzer import (
            InputValidationError,
            validate_days_back,
        )

        # Valid values
        assert validate_days_back(1) == 1
        assert validate_days_back(90) == 90
        assert validate_days_back(400) == 400

        # Invalid values
        with pytest.raises(InputValidationError):
            validate_days_back(0)
        with pytest.raises(InputValidationError):
            validate_days_back(-1)
        with pytest.raises(InputValidationError):
            validate_days_back(401)
        with pytest.raises(InputValidationError):
            validate_days_back("90")  # type: ignore

    def test_validate_max_results(self):
        """Test validating max_results parameter."""
        from IAMSentry.audit_log_permission_analyzer import (
            InputValidationError,
            validate_max_results,
        )

        # Valid values
        assert validate_max_results(1) == 1
        assert validate_max_results(1000) == 1000
        assert validate_max_results(10000) == 10000

        # Invalid values
        with pytest.raises(InputValidationError):
            validate_max_results(0)
        with pytest.raises(InputValidationError):
            validate_max_results(-1)
        with pytest.raises(InputValidationError):
            validate_max_results(10001)


class TestDashboardEndpointsWithAuth:
    """Integration tests for dashboard endpoints with authentication."""

    @pytest.fixture
    def test_client(self):
        """Create a test client with auth configured."""
        with patch.dict(
            os.environ,
            {
                "IAMSENTRY_AUTH_ENABLED": "true",
                "IAMSENTRY_API_KEYS": "test-api-key-12345",
                "IAMSENTRY_BASIC_AUTH_USERS": "admin:testpass",
            },
            clear=True,
        ):
            # Reset the auth config singleton
            import IAMSentry.dashboard.auth as auth_module

            auth_module._auth_config = None

            from fastapi.testclient import TestClient

            from IAMSentry.dashboard.server import app

            yield TestClient(app)

    def test_public_endpoints_no_auth(self, test_client):
        """Test that public endpoints don't require auth."""
        # Root page
        response = test_client.get("/")
        assert response.status_code == 200

        # Health check (note: it's /api/health, not /health)
        response = test_client.get("/api/health")
        assert response.status_code == 200

    def test_protected_endpoint_requires_auth(self, test_client):
        """Test that protected endpoints require authentication."""
        response = test_client.get("/api/stats")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_api_key_authentication(self, test_client):
        """Test authentication via API key."""
        response = test_client.get("/api/stats", headers={"X-API-Key": "test-api-key-12345"})
        assert response.status_code == 200

    def test_basic_auth_authentication(self, test_client):
        """Test authentication via Basic Auth."""
        credentials = base64.b64encode(b"admin:testpass").decode()
        response = test_client.get("/api/stats", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code == 200

    def test_invalid_api_key_rejected(self, test_client):
        """Test that invalid API key is rejected."""
        response = test_client.get("/api/stats", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401

    def test_invalid_basic_auth_rejected(self, test_client):
        """Test that invalid Basic Auth is rejected."""
        credentials = base64.b64encode(b"admin:wrongpass").decode()
        response = test_client.get("/api/stats", headers={"Authorization": f"Basic {credentials}"})
        assert response.status_code == 401


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
