"""Tests for GCP utility modules."""

from unittest.mock import MagicMock, patch

import pytest


class TestUtilGcp:
    """Tests for util_gcp module."""

    def test_get_credentials_with_key_file(self, temp_dir):
        """Test get_credentials with explicit key file."""
        # Create a mock key file
        key_file = temp_dir / "test-key.json"
        key_file.write_text("""{
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nMIItest\\n-----END PRIVATE KEY-----\\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }""")

        with patch("IAMSentry.plugins.gcp.util_gcp.service_account.Credentials") as mock_creds:
            mock_creds.from_service_account_file.return_value = MagicMock()

            from IAMSentry.plugins.gcp import util_gcp

            creds, project = util_gcp.get_credentials(str(key_file))

            mock_creds.from_service_account_file.assert_called_once()
            assert project == "test-project"

    def test_get_credentials_with_adc(self):
        """Test get_credentials falls back to ADC."""
        with patch("IAMSentry.plugins.gcp.util_gcp.google.auth.default") as mock_default:
            mock_creds = MagicMock()
            mock_default.return_value = (mock_creds, "adc-project")

            from IAMSentry.plugins.gcp import util_gcp

            creds, project = util_gcp.get_credentials()

            mock_default.assert_called_once()
            assert project == "adc-project"

    def test_get_credentials_file_not_found(self):
        """Test get_credentials raises error for missing key file."""
        from IAMSentry.plugins.gcp import util_gcp

        with pytest.raises(FileNotFoundError):
            util_gcp.get_credentials("/nonexistent/key.json")

    def test_get_credentials_gsm_reference(self):
        """Test get_credentials with Secret Manager reference."""
        with patch("IAMSentry.plugins.gcp.util_gcp._resolve_gsm_key_file") as mock_resolve:
            mock_resolve.return_value = None  # Simulate failed resolution

            with patch("IAMSentry.plugins.gcp.util_gcp.google.auth.default") as mock_default:
                mock_creds = MagicMock()
                mock_default.return_value = (mock_creds, "fallback-project")

                from IAMSentry.plugins.gcp import util_gcp

                creds, project = util_gcp.get_credentials("gsm://project/secret")

                # Should fall back to ADC when GSM resolution fails
                mock_default.assert_called_once()

    def test_build_resource(self):
        """Test build_resource creates API resource."""
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = (mock_creds, "test-project")

            with patch("IAMSentry.plugins.gcp.util_gcp.discovery.build") as mock_build:
                mock_resource = MagicMock()
                mock_build.return_value = mock_resource

                from IAMSentry.plugins.gcp import util_gcp

                resource = util_gcp.build_resource("cloudresourcemanager")

                mock_build.assert_called_once_with(
                    "cloudresourcemanager", "v1", credentials=mock_creds, cache_discovery=False
                )

    def test_set_service_account_legacy(self):
        """Test legacy set_service_account function."""
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = (mock_creds, "test-project")

            from IAMSentry.plugins.gcp import util_gcp

            creds = util_gcp.set_service_account()

            assert creds == mock_creds


class TestGCPCloudIAMRecommendations:
    """Tests for GCPCloudIAMRecommendations plugin."""

    def test_init_with_adc(self):
        """Test initialization with Application Default Credentials."""
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = (mock_creds, "test-project")

            from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations

            reader = GCPCloudIAMRecommendations(projects=["test-project"])

            assert reader._key_file_path is None
            assert reader._projects == ["test-project"]
            mock_get_creds.assert_called_once_with(None)

    def test_init_with_key_file(self, temp_dir):
        """Test initialization with explicit key file."""
        key_file = temp_dir / "test-key.json"
        key_file.write_text("""{
            "type": "service_account",
            "project_id": "test-project",
            "client_email": "test@test.iam.gserviceaccount.com"
        }""")

        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = (mock_creds, "test-project")

            from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations

            reader = GCPCloudIAMRecommendations(
                key_file_path=str(key_file), projects=["test-project"]
            )

            assert reader._key_file_path == str(key_file)

    def test_init_scan_all_projects(self):
        """Test initialization with wildcard projects."""
        with patch("IAMSentry.plugins.gcp.util_gcp.get_credentials") as mock_get_creds:
            mock_creds = MagicMock()
            mock_get_creds.return_value = (mock_creds, "test-project")

            with patch("IAMSentry.plugins.gcp.util_gcp.build_resource") as mock_build:
                mock_resource = MagicMock()
                mock_build.return_value = mock_resource

                with patch("IAMSentry.plugins.gcp.util_gcp.get_resource_iterator") as mock_iter:
                    mock_iter.return_value = iter(
                        [
                            {"projectId": "project-1", "lifecycleState": "ACTIVE"},
                            {"projectId": "project-2", "lifecycleState": "ACTIVE"},
                            {"projectId": "project-3", "lifecycleState": "DELETE_REQUESTED"},
                        ]
                    )

                    from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations

                    reader = GCPCloudIAMRecommendations(projects="*")

                    # Should only include ACTIVE projects
                    assert "project-1" in reader._projects
                    assert "project-2" in reader._projects
                    assert "project-3" not in reader._projects


class TestGCPIAMRemediationProcessor:
    """Tests for GCPIAMRemediationProcessor plugin."""

    def test_init_default_dry_run(self):
        """Test that dry_run defaults to True for safety."""
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

        processor = GCPIAMRemediationProcessor()

        assert processor._dry_run is True
        assert processor._mode_remediate is False

    def test_init_with_remediate_still_dry_run(self):
        """Test that dry_run is True even when remediation enabled."""
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

        processor = GCPIAMRemediationProcessor(mode_remediate=True)

        assert processor._dry_run is True
        assert processor._mode_remediate is True

    def test_simulate_remediation_remove_binding(self):
        """Test simulated removal of binding."""
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

        processor = GCPIAMRemediationProcessor(mode_remediate=True, dry_run=True)

        plan = {
            "account_id": "test@test.iam.gserviceaccount.com",
            "current_role": "roles/editor",
            "recommended_action": "remove_binding",
        }

        result = processor._simulate_remediation(plan)

        assert result["status"] == "simulated"
        assert result["action"] == "remove_binding"
        assert result["details"]["simulated"] is True

    def test_analyze_remediation_options_unused_role(self):
        """Test analysis of completely unused role."""
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

        processor = GCPIAMRemediationProcessor()

        record = {
            "processor": {
                "account_id": "test@test.iam.gserviceaccount.com",
                "account_type": "serviceAccount",
            },
            "score": {"over_privilege_score": 100, "risk_score": 80},
            "raw": {"content": {"overview": {"removedRole": "roles/editor"}}},
        }

        plan = processor._analyze_remediation_options(record)

        assert plan["recommended_action"] == "remove_binding"
        assert plan["waste_percentage"] == 100

    def test_safety_checks_critical_account(self):
        """Test safety checks detect critical accounts."""
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

        processor = GCPIAMRemediationProcessor()

        plan = {
            "account_id": "terraform-prod@project.iam.gserviceaccount.com",
            "recommended_action": "remove_binding",
        }

        record = {"raw": {}}

        checks = processor._perform_safety_checks(plan, record)

        # Should detect 'prod' and 'terraform' as critical patterns
        assert any("WARNING" in check for check in checks)


class TestValidationMixin:
    """Tests for ValidationMixin functionality."""

    def test_blocklist_validation_blocks_project(self):
        """Test that blocklisted projects are blocked."""
        from IAMSentry.plugins.gcp.base import ValidationMixin

        class TestProcessor(ValidationMixin):
            pass

        processor = TestProcessor()
        processor.init_validation_config({"blocklist_projects": ["blocked-project"]})

        result = processor.validate_blocklist("blocked-project", "user@example.com", "user")
        assert result is False

    def test_blocklist_validation_passes_allowed_project(self):
        """Test that non-blocklisted projects pass."""
        from IAMSentry.plugins.gcp.base import ValidationMixin

        class TestProcessor(ValidationMixin):
            pass

        processor = TestProcessor()
        processor.init_validation_config({"blocklist_projects": ["blocked-project"]})

        result = processor.validate_blocklist("allowed-project", "user@example.com", "user")
        assert result is True

    def test_allowlist_validation(self):
        """Test allowlist validation for account types."""
        from IAMSentry.plugins.gcp.base import ValidationMixin

        class TestProcessor(ValidationMixin):
            pass

        processor = TestProcessor()
        processor.init_validation_config({"allowlist_account_types": ["user", "group"]})

        assert processor.validate_allowlist(account_type="user") is True
        assert processor.validate_allowlist(account_type="group") is True
        assert processor.validate_allowlist(account_type="serviceAccount") is False

    def test_safety_score_validation(self):
        """Test safety score threshold validation."""
        from IAMSentry.plugins.gcp.base import ValidationMixin

        class TestProcessor(ValidationMixin):
            pass

        processor = TestProcessor()
        processor.init_validation_config({"min_safe_to_apply_score_user": 70})

        assert processor.validate_safety_score("user", 80) is True
        assert processor.validate_safety_score("user", 70) is True
        assert processor.validate_safety_score("user", 60) is False

    def test_critical_account_detection(self):
        """Test detection of critical accounts."""
        from IAMSentry.plugins.gcp.base import ValidationMixin

        class TestProcessor(ValidationMixin):
            pass

        processor = TestProcessor()
        processor.init_validation_config({})

        assert processor.is_critical_account("terraform-sa@project.iam.gserviceaccount.com") is True
        assert (
            processor.is_critical_account("prod-deployer@project.iam.gserviceaccount.com") is True
        )
        assert processor.is_critical_account("test-user@project.iam.gserviceaccount.com") is False


class TestIAMPolicyModifier:
    """Tests for IAMPolicyModifier utility."""

    def test_remove_member(self):
        """Test removing a member from a policy."""
        from IAMSentry.plugins.gcp.base import IAMPolicyModifier

        policy = {
            "bindings": [
                {
                    "role": "roles/editor",
                    "members": ["user:alice@example.com", "user:bob@example.com"],
                }
            ]
        }

        updated = IAMPolicyModifier.remove_member(policy, "roles/editor", "user:alice@example.com")

        assert "user:alice@example.com" not in updated["bindings"][0]["members"]
        assert "user:bob@example.com" in updated["bindings"][0]["members"]

    def test_add_member_to_existing_role(self):
        """Test adding a member to an existing role."""
        from IAMSentry.plugins.gcp.base import IAMPolicyModifier

        policy = {"bindings": [{"role": "roles/editor", "members": ["user:alice@example.com"]}]}

        updated = IAMPolicyModifier.add_member(policy, "roles/editor", "user:bob@example.com")

        assert "user:bob@example.com" in updated["bindings"][0]["members"]
        assert len(updated["bindings"][0]["members"]) == 2

    def test_add_member_to_new_role(self):
        """Test adding a member to a new role."""
        from IAMSentry.plugins.gcp.base import IAMPolicyModifier

        policy = {"bindings": [{"role": "roles/editor", "members": ["user:alice@example.com"]}]}

        updated = IAMPolicyModifier.add_member(policy, "roles/viewer", "user:bob@example.com")

        assert len(updated["bindings"]) == 2
        viewer_binding = next(b for b in updated["bindings"] if b["role"] == "roles/viewer")
        assert "user:bob@example.com" in viewer_binding["members"]

    def test_replace_role(self):
        """Test replacing a role for a member."""
        from IAMSentry.plugins.gcp.base import IAMPolicyModifier

        policy = {"bindings": [{"role": "roles/editor", "members": ["user:alice@example.com"]}]}

        updated = IAMPolicyModifier.replace_role(
            policy, "user:alice@example.com", "roles/editor", "roles/viewer"
        )

        # Check old role removed
        editor_binding = next((b for b in updated["bindings"] if b["role"] == "roles/editor"), None)
        assert editor_binding is None or "user:alice@example.com" not in editor_binding.get(
            "members", []
        )

        # Check new role added
        viewer_binding = next(b for b in updated["bindings"] if b["role"] == "roles/viewer")
        assert "user:alice@example.com" in viewer_binding["members"]

    def test_get_member_roles(self):
        """Test getting all roles for a member."""
        from IAMSentry.plugins.gcp.base import IAMPolicyModifier

        policy = {
            "bindings": [
                {"role": "roles/editor", "members": ["user:alice@example.com"]},
                {
                    "role": "roles/viewer",
                    "members": ["user:alice@example.com", "user:bob@example.com"],
                },
                {"role": "roles/admin", "members": ["user:bob@example.com"]},
            ]
        }

        roles = IAMPolicyModifier.get_member_roles(policy, "user:alice@example.com")

        assert "roles/editor" in roles
        assert "roles/viewer" in roles
        assert "roles/admin" not in roles
