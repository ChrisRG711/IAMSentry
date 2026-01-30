"""Tests for IAMSentry Dashboard module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDashboardImports:
    """Tests for dashboard module imports."""

    def test_dashboard_module_imports(self):
        """Test that dashboard module can be imported."""
        from IAMSentry.dashboard import __version__
        assert __version__ is not None

    def test_dashboard_server_imports(self):
        """Test that dashboard server can be imported."""
        from IAMSentry.dashboard.server import app
        assert app is not None

    def test_dashboard_models_import(self):
        """Test that Pydantic models can be imported."""
        from IAMSentry.dashboard.server import (
            ScanRequest,
            ScanStatus,
            Recommendation,
            DashboardStats,
            RemediationRequest,
            RemediationResult,
        )
        assert ScanRequest is not None
        assert ScanStatus is not None


class TestDashboardApp:
    """Tests for FastAPI application."""

    def test_app_has_routes(self):
        """Test that app has expected routes."""
        from IAMSentry.dashboard.server import app

        routes = [route.path for route in app.routes]

        assert "/" in routes
        assert "/api/health" in routes
        assert "/api/stats" in routes
        assert "/api/recommendations" in routes
        assert "/api/projects" in routes
        assert "/api/scan" in routes
        assert "/api/remediate" in routes
        assert "/api/auth/status" in routes

    def test_app_title(self):
        """Test app title and metadata."""
        from IAMSentry.dashboard.server import app

        assert app.title == "IAMSentry Dashboard"
        assert "0.4.0" in app.version


class TestDashboardModels:
    """Tests for Pydantic models."""

    def test_scan_request_defaults(self):
        """Test ScanRequest model with defaults."""
        from IAMSentry.dashboard.server import ScanRequest

        request = ScanRequest()
        assert request.projects == ["*"]
        assert request.dry_run is True

    def test_scan_request_custom(self):
        """Test ScanRequest model with custom values."""
        from IAMSentry.dashboard.server import ScanRequest

        request = ScanRequest(projects=["project-1", "project-2"], dry_run=False)
        assert request.projects == ["project-1", "project-2"]
        assert request.dry_run is False

    def test_scan_status_model(self):
        """Test ScanStatus model."""
        from IAMSentry.dashboard.server import ScanStatus

        status = ScanStatus(
            id="scan_123",
            status="running",
            started_at="2024-01-01T00:00:00Z",
            projects=["test-project"],
        )
        assert status.id == "scan_123"
        assert status.status == "running"
        assert status.recommendation_count == 0

    def test_recommendation_model(self):
        """Test Recommendation model."""
        from IAMSentry.dashboard.server import Recommendation

        rec = Recommendation(
            id="rec123",
            project="test-project",
            account_id="test@test.iam.gserviceaccount.com",
            account_type="serviceAccount",
            current_role="roles/editor",
            recommended_action="REMOVE_ROLE",
            risk_score=75,
            waste_percentage=50,
            safe_to_apply_score=80,
            priority="P2",
            state="ACTIVE",
        )
        assert rec.risk_score == 75
        assert rec.account_type == "serviceAccount"

    def test_dashboard_stats_model(self):
        """Test DashboardStats model."""
        from IAMSentry.dashboard.server import DashboardStats

        stats = DashboardStats(
            total_recommendations=100,
            high_risk_count=20,
            medium_risk_count=30,
            low_risk_count=50,
            service_accounts=60,
            users=30,
            groups=10,
            projects_scanned=5,
        )
        assert stats.total_recommendations == 100
        assert stats.high_risk_count == 20

    def test_remediation_request_defaults(self):
        """Test RemediationRequest model with defaults."""
        from IAMSentry.dashboard.server import RemediationRequest

        request = RemediationRequest(recommendation_id="rec123")
        assert request.recommendation_id == "rec123"
        assert request.dry_run is True

    def test_remediation_result_model(self):
        """Test RemediationResult model."""
        from IAMSentry.dashboard.server import RemediationResult

        result = RemediationResult(
            recommendation_id="rec123",
            status="success",
            action="REMOVE_ROLE",
            details={"member": "test@test.iam.gserviceaccount.com"},
        )
        assert result.status == "success"
        assert result.action == "REMOVE_ROLE"


class TestDashboardHelpers:
    """Tests for helper functions."""

    def test_extract_role(self):
        """Test _extract_role helper."""
        from IAMSentry.dashboard.server import _extract_role

        raw = {
            "content": {
                "operationGroups": [
                    {
                        "operations": [
                            {
                                "action": "remove",
                                "pathFilters": {
                                    "/iamPolicy/bindings/*/role": "roles/editor"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        assert _extract_role(raw) == "roles/editor"

    def test_extract_role_empty(self):
        """Test _extract_role with empty input."""
        from IAMSentry.dashboard.server import _extract_role

        assert _extract_role({}) == "N/A"
        assert _extract_role({"content": {}}) == "N/A"

    def test_get_dashboard_html(self):
        """Test get_dashboard_html returns valid HTML."""
        from IAMSentry.dashboard.server import get_dashboard_html

        html = get_dashboard_html()

        assert "<!DOCTYPE html>" in html
        assert "IAMSentry Dashboard" in html
        assert "vue" in html.lower()
        assert "tailwind" in html.lower()


class TestDashboardEndpoints:
    """Tests for API endpoints using TestClient."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from IAMSentry.dashboard.server import app

        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test /api/health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self, client):
        """Test / endpoint returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "IAMSentry Dashboard" in response.text

    def test_stats_endpoint(self, client, temp_dir):
        """Test /api/stats endpoint."""
        # Set up empty data dir
        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_dir

        try:
            response = client.get("/api/stats")
            assert response.status_code == 200

            data = response.json()
            assert "total_recommendations" in data
            assert "high_risk_count" in data
        finally:
            server.DATA_DIR = original_dir

    def test_recommendations_endpoint(self, client, temp_dir):
        """Test /api/recommendations endpoint."""
        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_dir

        try:
            response = client.get("/api/recommendations")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        finally:
            server.DATA_DIR = original_dir

    def test_recommendations_with_filters(self, client, temp_dir):
        """Test /api/recommendations with filters."""
        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_dir

        # Create test data file
        test_data = [
            {
                "processor": {
                    "project": "test-project",
                    "account_id": "test@test.iam.gserviceaccount.com",
                    "account_type": "serviceAccount",
                    "recommendetion_recommender_subtype": "REMOVE_ROLE"
                },
                "score": {
                    "risk_score": 75,
                    "over_privilege_score": 50,
                    "safe_to_apply_recommendation_score": 80
                },
                "raw": {
                    "name": "projects/test/recommendations/abc123",
                    "priority": "P2",
                    "stateInfo": {"state": "ACTIVE"}
                }
            }
        ]
        with open(temp_dir / "results.json", 'w') as f:
            json.dump(test_data, f)

        try:
            response = client.get("/api/recommendations?account_type=serviceAccount&min_risk=50")
            assert response.status_code == 200
        finally:
            server.DATA_DIR = original_dir

    def test_projects_endpoint(self, client, temp_dir):
        """Test /api/projects endpoint."""
        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_dir

        try:
            response = client.get("/api/projects")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        finally:
            server.DATA_DIR = original_dir

    def test_scan_endpoint(self, client):
        """Test /api/scan endpoint."""
        response = client.post("/api/scan", json={"projects": ["*"], "dry_run": True})
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["status"] == "running"

    def test_remediate_not_found(self, client, temp_dir):
        """Test /api/remediate with non-existent recommendation."""
        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_dir

        try:
            response = client.post("/api/remediate", json={
                "recommendation_id": "nonexistent",
                "dry_run": True
            })
            assert response.status_code == 404
        finally:
            server.DATA_DIR = original_dir

    def test_auth_status_endpoint(self, client):
        """Test /api/auth/status endpoint."""
        with patch('IAMSentry.plugins.gcp.util_gcp.get_credentials') as mock_creds:
            mock_cred_obj = MagicMock()
            mock_cred_obj.service_account_email = "test@test.iam.gserviceaccount.com"
            mock_creds.return_value = (mock_cred_obj, "test-project")

            response = client.get("/api/auth/status")
            assert response.status_code == 200

    def test_auth_status_not_authenticated(self, client):
        """Test /api/auth/status when not authenticated."""
        with patch('IAMSentry.plugins.gcp.util_gcp.get_credentials') as mock_creds:
            mock_creds.side_effect = Exception("Not authenticated")

            response = client.get("/api/auth/status")
            assert response.status_code == 200

            data = response.json()
            assert data["authenticated"] is False


class TestDashboardDataLoading:
    """Tests for data loading functionality."""

    @pytest.fixture
    def temp_data_dir(self, temp_dir):
        """Create a temporary data directory."""
        data_dir = temp_dir / "output"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def test_load_recommendations_empty_dir(self, temp_data_dir):
        """Test loading recommendations from empty directory."""
        import asyncio
        from IAMSentry.dashboard.server import load_recommendations, DATA_DIR

        # Temporarily override DATA_DIR
        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_data_dir

        try:
            result = asyncio.run(load_recommendations())
            assert result == []
        finally:
            server.DATA_DIR = original_dir

    def test_load_recommendations_with_files(self, temp_data_dir):
        """Test loading recommendations from files."""
        import asyncio
        from IAMSentry.dashboard.server import load_recommendations

        # Create test data file
        test_data = [
            {"processor": {"project": "test"}, "score": {"risk_score": 50}},
            {"processor": {"project": "test2"}, "score": {"risk_score": 75}}
        ]
        with open(temp_data_dir / "results.json", 'w') as f:
            json.dump(test_data, f)

        import IAMSentry.dashboard.server as server
        original_dir = server.DATA_DIR
        server.DATA_DIR = temp_data_dir

        try:
            result = asyncio.run(load_recommendations())
            assert len(result) == 2
        finally:
            server.DATA_DIR = original_dir


class TestDashboardMain:
    """Tests for main function."""

    def test_main_function_exists(self):
        """Test that main function exists."""
        from IAMSentry.dashboard.server import main
        assert callable(main)
