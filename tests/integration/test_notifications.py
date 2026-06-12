import pytest


@pytest.mark.integration
@pytest.mark.notifications
class TestGetNotifications:

    def test_get_notifications_success(self, client, notifications_url, user_auth_headers, test_notification):
        """Should return user notifications"""
        response = client.get(f"{notifications_url}/", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notifications" in data["data"]
        assert "unread_count" in data["data"]

    def test_get_notifications_without_auth(self, client, notifications_url):
        """Should fail without authentication"""
        response = client.get(f"{notifications_url}/")
        assert response.status_code == 403

    def test_get_unread_count(self, client, notifications_url, user_auth_headers, test_notification):
        """Should return unread count"""
        response = client.get(f"{notifications_url}/unread/count", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data["data"]
        assert data["data"]["unread_count"] >= 1

    def test_get_notifications_filter_unread(self, client, notifications_url, user_auth_headers, test_notification):
        """Should filter by read status"""
        response = client.get(
            f"{notifications_url}/?is_read=false",
            headers=user_auth_headers
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.notifications
class TestMarkNotificationsRead:

    def test_mark_all_read(self, client, notifications_url, user_auth_headers, test_notification):
        """Should mark all notifications as read"""
        response = client.post(
            f"{notifications_url}/mark-read",
            json={"notification_ids": None},
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["marked_count"] >= 0

    def test_mark_specific_notification_read(self, client, notifications_url, user_auth_headers, test_notification):
        """Should mark specific notification as read"""
        response = client.post(
            f"{notifications_url}/mark-read",
            json={"notification_ids": [test_notification.id]},
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["marked_count"] == 1

    def test_mark_read_without_auth(self, client, notifications_url):
        """Should fail without authentication"""
        response = client.post(
            f"{notifications_url}/mark-read",
            json={"notification_ids": None}
        )
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.notifications
class TestDeleteNotification:

    def test_delete_notification_success(self, client, notifications_url, user_auth_headers, test_notification):
        """Should delete notification"""
        response = client.delete(
            f"{notifications_url}/{test_notification.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_nonexistent_notification(self, client, notifications_url, user_auth_headers):
        """Should return 404 for non-existent notification"""
        response = client.delete(
            f"{notifications_url}/99999",
            headers=user_auth_headers
        )
        assert response.status_code == 404

    def test_delete_without_auth(self, client, notifications_url, test_notification):
        """Should fail without authentication"""
        response = client.delete(f"{notifications_url}/{test_notification.id}")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.notifications
class TestNotificationPreferences:

    def test_get_preferences(self, client, notifications_url, user_auth_headers):
        """Should return notification preferences"""
        response = client.get(
            f"{notifications_url}/preferences",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "email_enabled" in data["data"]

    def test_update_preferences(self, client, notifications_url, user_auth_headers):
        """Should update notification preferences"""
        response = client.put(
            f"{notifications_url}/preferences",
            json={"email_enabled": False, "in_app_enabled": True},
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["email_enabled"] is False

    def test_get_preferences_without_auth(self, client, notifications_url):
        """Should fail without authentication"""
        response = client.get(f"{notifications_url}/preferences")
        assert response.status_code == 403