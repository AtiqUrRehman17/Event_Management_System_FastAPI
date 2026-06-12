import pytest
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.bookings
class TestCreateBooking:

    def test_create_booking_success(self, client, bookings_url, user_auth_headers, test_event):
        """Should create booking successfully"""
        with patch("app.services.notification_service.NotificationService.send_booking_confirmation"):
            response = client.post(f"{bookings_url}/", json={
                "event_id": test_event.id,
                "number_of_seats": 2
            }, headers=user_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["number_of_seats"] == 2
        assert data["data"]["total_price"] == 100.00

    def test_create_booking_without_auth(self, client, bookings_url, test_event):
        """Should fail without authentication"""
        response = client.post(f"{bookings_url}/", json={
            "event_id": test_event.id,
            "number_of_seats": 1
        })
        assert response.status_code == 403

    def test_create_booking_nonexistent_event(self, client, bookings_url, user_auth_headers):
        """Should fail for non-existent event"""
        response = client.post(f"{bookings_url}/", json={
            "event_id": 99999,
            "number_of_seats": 1
        }, headers=user_auth_headers)
        assert response.status_code == 404

    def test_create_booking_sold_out_event(self, client, bookings_url, user_auth_headers, test_event_sold_out):
        """Should offer waitlist for sold out event"""
        response = client.post(f"{bookings_url}/", json={
            "event_id": test_event_sold_out.id,
            "number_of_seats": 1
        }, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "waitlist" in data["data"]["message"].lower() or \
               "sold out" in data["data"]["message"].lower()

    def test_create_booking_cancelled_event(self, client, bookings_url, user_auth_headers, test_event_cancelled):
        """Should fail for cancelled event"""
        response = client.post(f"{bookings_url}/", json={
            "event_id": test_event_cancelled.id,
            "number_of_seats": 1
        }, headers=user_auth_headers)
        assert response.status_code == 400

    def test_create_booking_zero_seats(self, client, bookings_url, user_auth_headers, test_event):
        """Should fail with zero seats"""
        response = client.post(f"{bookings_url}/", json={
            "event_id": test_event.id,
            "number_of_seats": 0
        }, headers=user_auth_headers)
        assert response.status_code == 422

    def test_create_booking_reduces_available_seats(self, client, bookings_url, user_auth_headers, test_event, db):
        """Booking should reduce available seats"""
        initial_seats = test_event.available_seats
        with patch("app.services.notification_service.NotificationService.send_booking_confirmation"):
            client.post(f"{bookings_url}/", json={
                "event_id": test_event.id,
                "number_of_seats": 2
            }, headers=user_auth_headers)

        db.refresh(test_event)
        assert test_event.available_seats == initial_seats - 2


@pytest.mark.integration
@pytest.mark.bookings
class TestGetMyBookings:

    def test_get_my_bookings(self, client, bookings_url, user_auth_headers, test_booking):
        """Should return user's bookings"""
        response = client.get(f"{bookings_url}/me", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_my_bookings_without_auth(self, client, bookings_url):
        """Should fail without authentication"""
        response = client.get(f"{bookings_url}/me")
        assert response.status_code == 403

    def test_get_my_bookings_with_status_filter(self, client, bookings_url, user_auth_headers, test_booking):
        """Should filter bookings by status"""
        response = client.get(
            f"{bookings_url}/me?status=active",
            headers=user_auth_headers
        )
        assert response.status_code == 200

    def test_get_booking_history(self, client, bookings_url, user_auth_headers, test_booking):
        """Should return booking history"""
        response = client.get(f"{bookings_url}/history", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_booking_summary(self, client, bookings_url, user_auth_headers, test_booking):
        """Should return booking summary"""
        response = client.get(f"{bookings_url}/me/summary", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_booking_statistics(self, client, bookings_url, user_auth_headers, test_booking):
        """Should return booking statistics"""
        response = client.get(f"{bookings_url}/statistics", headers=user_auth_headers)
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.bookings
class TestGetBookingById:

    def test_get_own_booking(self, client, bookings_url, user_auth_headers, test_booking):
        """Should get own booking by ID"""
        response = client.get(
            f"{bookings_url}/{test_booking.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_booking.id

    def test_get_other_user_booking(self, client, bookings_url, admin_auth_headers, test_booking):
        """Admin can get any booking"""
        response = client.get(
            f"{bookings_url}/{test_booking.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_get_nonexistent_booking(self, client, bookings_url, user_auth_headers):
        """Should return 404 for non-existent booking"""
        response = client.get(
            f"{bookings_url}/99999",
            headers=user_auth_headers
        )
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.bookings
class TestCancelBooking:

    def test_cancel_own_booking(self, client, bookings_url, user_auth_headers, test_booking):
        """Should cancel own booking"""
        with patch("app.services.notification_service.NotificationService.send_booking_cancellation"), \
             patch("app.services.waitlist_service.WaitlistService.process_cancellation"):
            response = client.post(
                f"{bookings_url}/{test_booking.id}/cancel",
                headers=user_auth_headers
            )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "cancelled"

    def test_cancel_already_cancelled_booking(self, client, bookings_url, user_auth_headers, test_booking_cancelled):
        """Should fail cancelling already cancelled booking"""
        response = client.post(
            f"{bookings_url}/{test_booking_cancelled.id}/cancel",
            headers=user_auth_headers
        )
        assert response.status_code == 400

    def test_cancel_booking_without_auth(self, client, bookings_url, test_booking):
        """Should fail without authentication"""
        response = client.post(f"{bookings_url}/{test_booking.id}/cancel")
        assert response.status_code == 403

    def test_admin_can_cancel_any_booking(self, client, bookings_url, admin_auth_headers, test_booking):
        """Admin should cancel any booking"""
        with patch("app.services.notification_service.NotificationService.send_booking_cancellation"), \
             patch("app.services.waitlist_service.WaitlistService.process_cancellation"):
            response = client.post(
                f"{bookings_url}/{test_booking.id}/cancel",
                headers=admin_auth_headers
            )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.bookings
class TestAdminBookings:

    def test_get_all_bookings_as_admin(self, client, bookings_url, admin_auth_headers, test_booking):
        """Admin should get all bookings"""
        response = client.get(f"{bookings_url}/", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_all_bookings_as_user(self, client, bookings_url, user_auth_headers):
        """Regular user should not get all bookings"""
        response = client.get(f"{bookings_url}/", headers=user_auth_headers)
        assert response.status_code == 403

    def test_get_event_bookings_as_admin(self, client, bookings_url, admin_auth_headers, test_booking, test_event):
        """Admin should get bookings for specific event"""
        response = client.get(
            f"{bookings_url}/events/{test_event.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True