import pytest


@pytest.mark.integration
@pytest.mark.audit
class TestGetAuditLogs:

    def test_get_audit_logs_as_admin(self, client, audit_url, admin_auth_headers, test_user):
        """Admin should get audit logs"""
        response = client.get(f"{audit_url}/logs", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "logs" in data["data"]
        assert "total" in data["data"]

    def test_get_audit_logs_as_user(self, client, audit_url, user_auth_headers):
        """Regular user should not access audit logs"""
        response = client.get(f"{audit_url}/logs", headers=user_auth_headers)
        assert response.status_code == 403

    def test_get_audit_logs_without_auth(self, client, audit_url):
        """Should fail without authentication"""
        response = client.get(f"{audit_url}/logs")
        assert response.status_code == 403

    def test_get_audit_logs_filter_by_category(self, client, audit_url, admin_auth_headers):
        """Should filter audit logs by category"""
        response = client.get(
            f"{audit_url}/logs?category=auth",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_get_audit_logs_filter_by_user(self, client, audit_url, admin_auth_headers, test_user):
        """Should filter audit logs by user"""
        response = client.get(
            f"{audit_url}/logs?user_id={test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_get_audit_logs_pagination(self, client, audit_url, admin_auth_headers):
        """Should paginate audit logs"""
        response = client.get(
            f"{audit_url}/logs?page=1&limit=10",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data["data"]
        assert "total_pages" in data["data"]


@pytest.mark.integration
@pytest.mark.audit
class TestAuditSummary:

    def test_get_audit_summary(self, client, audit_url, admin_auth_headers):
        """Admin should get audit summary"""
        response = client.get(f"{audit_url}/summary", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_logs" in data["data"]
        assert "logs_by_category" in data["data"]

    def test_get_audit_summary_as_user(self, client, audit_url, user_auth_headers):
        """Regular user should not get audit summary"""
        response = client.get(f"{audit_url}/summary", headers=user_auth_headers)
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.audit
class TestUserAuditTrail:

    def test_get_user_audit_trail(self, client, audit_url, admin_auth_headers, test_user):
        """Admin should get user audit trail"""
        response = client.get(
            f"{audit_url}/user/{test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "audit_trail" in data["data"]

    def test_get_user_audit_trail_as_user(self, client, audit_url, user_auth_headers, test_user):
        """Regular user should not get audit trail"""
        response = client.get(
            f"{audit_url}/user/{test_user.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.audit
class TestEntityAuditTrail:

    def test_get_entity_audit_trail(self, client, audit_url, admin_auth_headers, test_event):
        """Admin should get entity audit trail"""
        response = client.get(
            f"{audit_url}/entity/event/{test_event.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "audit_trail" in data["data"]

    def test_get_entity_audit_trail_as_user(self, client, audit_url, user_auth_headers, test_event):
        """Regular user should not get entity audit trail"""
        response = client.get(
            f"{audit_url}/entity/event/{test_event.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 403