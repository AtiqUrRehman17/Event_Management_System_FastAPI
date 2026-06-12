import pytest
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.waitlist
class TestJoinWaitlist:

    def test_join_waitlist_success(self, client, waitlist_url, user_auth_headers, test_event_sold_out):
        """Should join waitlist for sold out event"""
        with patch("app.services.email_service.EmailService.send_waitlist_joined_email", return_value=True), \
             patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(
                f"{waitlist_url}/{test_event_sold_out.id}/join",
                headers=user_auth_headers
            )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["position"] == 1

    def test_join_waitlist_without_auth(self, client, waitlist_url, test_event_sold_out):
        """Should fail without authentication"""
        response = client.post(f"{waitlist_url}/{test_event_sold_out.id}/join")
        assert response.status_code == 403

    def test_join_waitlist_available_event(self, client, waitlist_url, user_auth_headers, test_event):
        """Should fail for event with available seats"""
        response = client.post(
            f"{waitlist_url}/{test_event.id}/join",
            headers=user_auth_headers
        )
        assert response.status_code == 400

    def test_join_waitlist_twice(self, client, waitlist_url, user_auth_headers, test_event_sold_out, test_waitlist_entry):
        """Should fail when already on waitlist"""
        response = client.post(
            f"{waitlist_url}/{test_event_sold_out.id}/join",
            headers=user_auth_headers
        )
        assert response.status_code == 400

    def test_join_nonexistent_event(self, client, waitlist_url, user_auth_headers):
        """Should fail for non-existent event"""
        response = client.post(
            f"{waitlist_url}/99999/join",
            headers=user_auth_headers
        )
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.waitlist
class TestGetWaitlistPosition:

    def test_get_position_success(self, client, waitlist_url, user_auth_headers, test_waitlist_entry, test_event_sold_out):
        """Should return user's waitlist position"""
        response = client.get(
            f"{waitlist_url}/{test_event_sold_out.id}/position",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["position"] == 1

    def test_get_position_not_on_waitlist(self, client, waitlist_url, user_auth_headers, test_event_sold_out):
        """Should return not on waitlist message"""
        response = client.get(
            f"{waitlist_url}/{test_event_sold_out.id}/position",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["position"] is None

    def test_get_position_without_auth(self, client, waitlist_url, test_event_sold_out):
        """Should fail without authentication"""
        response = client.get(f"{waitlist_url}/{test_event_sold_out.id}/position")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.waitlist
class TestLeaveWaitlist:

    def test_leave_waitlist_success(self, client, waitlist_url, user_auth_headers, test_waitlist_entry, test_event_sold_out):
        """Should leave waitlist successfully"""
        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.delete(
                f"{waitlist_url}/{test_event_sold_out.id}/leave",
                headers=user_auth_headers
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_leave_waitlist_not_on_it(self, client, waitlist_url, user_auth_headers, test_event_sold_out):
        """Should fail when not on waitlist"""
        response = client.delete(
            f"{waitlist_url}/{test_event_sold_out.id}/leave",
            headers=user_auth_headers
        )
        assert response.status_code == 404

    def test_leave_waitlist_without_auth(self, client, waitlist_url, test_event_sold_out):
        """Should fail without authentication"""
        response = client.delete(f"{waitlist_url}/{test_event_sold_out.id}/leave")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.waitlist
class TestWaitlistSummary:

    def test_get_summary(self, client, waitlist_url, user_auth_headers, test_event_sold_out):
        """Should return waitlist summary"""
        response = client.get(
            f"{waitlist_url}/{test_event_sold_out.id}/summary",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_waiting" in data["data"]

    def test_get_admin_waitlist(self, client, waitlist_url, admin_auth_headers, test_event_sold_out):
        """Admin should get full waitlist"""
        response = client.get(
            f"{waitlist_url}/admin/{test_event_sold_out.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True