import pytest
from datetime import datetime, timedelta


@pytest.mark.integration
@pytest.mark.events
class TestGetEvents:

    def test_get_all_events(self, client, events_url, test_event):
        """Should return all upcoming events"""
        response = client.get(f"{events_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_events_no_auth_required(self, client, events_url):
        """Should work without authentication"""
        response = client.get(f"{events_url}/")
        assert response.status_code == 200

    def test_get_events_with_search(self, client, events_url, test_event):
        """Should filter events by search term"""
        response = client.get(f"{events_url}/?search=Test Event")
        assert response.status_code == 200

    def test_get_events_with_category_filter(self, client, events_url, test_event, test_category):
        """Should filter events by category"""
        response = client.get(f"{events_url}/?category_id={test_category.id}")
        assert response.status_code == 200

    def test_get_events_with_price_filter(self, client, events_url, test_event):
        """Should filter events by price range"""
        response = client.get(f"{events_url}/?min_price=0&max_price=100")
        assert response.status_code == 200

    def test_get_events_pagination(self, client, events_url, test_event):
        """Should paginate events"""
        response = client.get(f"{events_url}/?page=1&limit=5")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.events
class TestGetEventById:

    def test_get_event_success(self, client, events_url, test_event):
        """Should return event by ID"""
        response = client.get(f"{events_url}/{test_event.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_event.id
        assert data["data"]["title"] == "Test Event"

    def test_get_nonexistent_event(self, client, events_url):
        """Should return 404 for non-existent event"""
        response = client.get(f"{events_url}/99999")
        assert response.status_code == 404

    def test_get_deleted_event_returns_404(self, client, events_url, test_deleted_event):
        """Soft deleted event should return 404 for regular users"""
        response = client.get(f"{events_url}/{test_deleted_event.id}")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.events
class TestCreateEvent:

    def test_create_event_as_admin(self, client, events_url, admin_auth_headers, test_category):
        """Admin should create event successfully"""
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        response = client.post(f"{events_url}/", json={
            "title": "New Test Event",
            "description": "A new test event",
            "location": "Test City",
            "event_date": future_date,
            "total_seats": 100,
            "price": 50.00,
            "category_id": test_category.id
        }, headers=admin_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "New Test Event"
        assert data["data"]["available_seats"] == 100

    def test_create_event_as_user(self, client, events_url, user_auth_headers, test_category):
        """Regular user should not create event"""
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        response = client.post(f"{events_url}/", json={
            "title": "New Event",
            "description": "Test",
            "location": "City",
            "event_date": future_date,
            "total_seats": 50,
            "price": 25.00
        }, headers=user_auth_headers)
        assert response.status_code == 403

    def test_create_event_past_date(self, client, events_url, admin_auth_headers):
        """Should fail with past event date"""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        response = client.post(f"{events_url}/", json={
            "title": "Past Event",
            "description": "Test",
            "location": "City",
            "event_date": past_date,
            "total_seats": 50,
            "price": 25.00
        }, headers=admin_auth_headers)
        assert response.status_code == 422

    def test_create_event_missing_fields(self, client, events_url, admin_auth_headers):
        """Should fail with missing required fields"""
        response = client.post(f"{events_url}/", json={
            "title": "Incomplete Event"
        }, headers=admin_auth_headers)
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.events
class TestUpdateEvent:

    def test_update_event_as_admin(self, client, events_url, admin_auth_headers, test_event):
        """Admin should update event"""
        response = client.put(f"{events_url}/{test_event.id}", json={
            "title": "Updated Event Title",
            "price": 75.00
        }, headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Event Title"
        assert data["data"]["price"] == 75.00

    def test_update_event_as_user(self, client, events_url, user_auth_headers, test_event):
        """Regular user should not update event"""
        response = client.put(f"{events_url}/{test_event.id}", json={
            "title": "Updated"
        }, headers=user_auth_headers)
        assert response.status_code == 403

    def test_update_nonexistent_event(self, client, events_url, admin_auth_headers):
        """Should return 404 for non-existent event"""
        response = client.put(f"{events_url}/99999", json={
            "title": "Updated"
        }, headers=admin_auth_headers)
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.events
class TestDeleteEvent:

    def test_soft_delete_event(self, client, events_url, admin_auth_headers, test_event):
        """Admin should soft delete event"""
        response = client.delete(
            f"{events_url}/{test_event.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_deleted"] is True

    def test_delete_event_as_user(self, client, events_url, user_auth_headers, test_event):
        """Regular user should not delete event"""
        response = client.delete(
            f"{events_url}/{test_event.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 403

    def test_restore_deleted_event(self, client, events_url, admin_auth_headers, test_deleted_event):
        """Admin should restore soft deleted event"""
        response = client.post(
            f"{events_url}/{test_deleted_event.id}/restore",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_deleted"] is False

    def test_get_deleted_events(self, client, events_url, admin_auth_headers, test_deleted_event):
        """Admin should get deleted events"""
        response = client.get(
            f"{events_url}/deleted",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True