"""Integration tests for Payment endpoints"""
import pytest
from unittest.mock import patch

from app.core.enums import PaymentStatus, PaymentMethod


@pytest.mark.integration
@pytest.mark.payments
class TestInitiatePayment:

    def test_initiate_payment_success(self, client, api_prefix, user_auth_headers, test_booking, db):
        """Should initiate payment successfully for own active booking"""
        url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["payment"]["booking_id"] == test_booking.id
        assert data["data"]["payment"]["status"] == "pending"
        assert data["data"]["payment"]["amount"] == test_booking.total_price
        assert data["data"]["payment_url"] is not None

    def test_initiate_payment_without_auth(self, client, api_prefix, test_booking):
        """Should fail without authentication"""
        url = f"{api_prefix}/payments/initiate"
        response = client.post(url, json={
            "booking_id": test_booking.id,
            "payment_method": "credit_card"
        })
        assert response.status_code == 403

    def test_initiate_payment_nonexistent_booking(self, client, api_prefix, user_auth_headers):
        """Should fail for non-existent booking"""
        url = f"{api_prefix}/payments/initiate"
        response = client.post(url, json={
            "booking_id": 99999,
            "payment_method": "credit_card"
        }, headers=user_auth_headers)
        assert response.status_code == 404

    def test_initiate_payment_other_user_booking(self, client, api_prefix, admin_auth_headers, test_booking):
        """Should fail for another user's booking"""
        url = f"{api_prefix}/payments/initiate"
        response = client.post(url, json={
            "booking_id": test_booking.id,
            "payment_method": "credit_card"
        }, headers=admin_auth_headers)
        assert response.status_code == 403

    def test_initiate_payment_cancelled_booking(self, client, api_prefix, user_auth_headers, test_booking_cancelled):
        """Should fail for cancelled booking"""
        url = f"{api_prefix}/payments/initiate"
        response = client.post(url, json={
            "booking_id": test_booking_cancelled.id,
            "payment_method": "credit_card"
        }, headers=user_auth_headers)
        assert response.status_code == 400

    def test_initiate_duplicate_payment(self, client, api_prefix, user_auth_headers, test_booking):
        """Should fail when payment already exists for this booking"""
        url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            client.post(url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)

        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(url, json={
                "booking_id": test_booking.id,
                "payment_method": "paypal"
            }, headers=user_auth_headers)
        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.payments
class TestSimulatePayment:

    def test_simulate_payment_success(self, client, api_prefix, user_auth_headers, test_booking, db):
        """Should simulate successful payment and update booking"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        sim_url = f"{api_prefix}/payments/simulate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(sim_url, json={
                "payment_id": payment_id,
                "success": True,
                "gateway_transaction_id": "gtx_12345"
            }, headers=user_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["payment"]["status"] == "paid"
        assert data["data"]["payment"]["gateway_transaction_id"] == "gtx_12345"
        assert data["data"]["booking_payment_status"] == "paid"

        db.refresh(test_booking)
        assert test_booking.payment_status == PaymentStatus.PAID
        assert test_booking.payment_transaction_id is not None
        assert test_booking.paid_at is not None

    def test_simulate_payment_failure(self, client, api_prefix, user_auth_headers, test_booking, db):
        """Should simulate failed payment and update booking"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        sim_url = f"{api_prefix}/payments/simulate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(sim_url, json={
                "payment_id": payment_id,
                "success": False,
                "failure_reason": "Insufficient funds"
            }, headers=user_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["payment"]["status"] == "failed"
        assert data["data"]["payment"]["failure_reason"] == "Insufficient funds"
        assert data["data"]["booking_payment_status"] == "failed"

        db.refresh(test_booking)
        assert test_booking.payment_status == PaymentStatus.FAILED

    def test_simulate_already_paid(self, client, api_prefix, user_auth_headers, test_booking):
        """Should fail when payment already completed"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        sim_url = f"{api_prefix}/payments/simulate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            client.post(sim_url, json={
                "payment_id": payment_id,
                "success": True
            }, headers=user_auth_headers)

        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(sim_url, json={
                "payment_id": payment_id,
                "success": True
            }, headers=user_auth_headers)
        assert response.status_code == 400

    def test_simulate_payment_without_auth(self, client, api_prefix):
        """Should fail without authentication"""
        url = f"{api_prefix}/payments/simulate"
        response = client.post(url, json={
            "payment_id": 1,
            "success": True
        })
        assert response.status_code == 403

    def test_simulate_nonexistent_payment(self, client, api_prefix, user_auth_headers):
        """Should fail for non-existent payment"""
        url = f"{api_prefix}/payments/simulate"
        response = client.post(url, json={
            "payment_id": 99999,
            "success": True
        }, headers=user_auth_headers)
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.payments
class TestRefundPayment:

    def setup_paid_payment(self, client, api_prefix, user_auth_headers, test_booking):
        """Helper: create an initiate and pay a booking"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        sim_url = f"{api_prefix}/payments/simulate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            client.post(sim_url, json={
                "payment_id": payment_id,
                "success": True
            }, headers=user_auth_headers)
        return payment_id

    def test_full_refund(self, client, api_prefix, user_auth_headers, test_booking, db):
        """Should process full refund"""
        payment_id = self.setup_paid_payment(client, api_prefix, user_auth_headers, test_booking)

        refund_url = f"{api_prefix}/payments/{payment_id}/refund"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(refund_url, json={"payment_id": payment_id}, headers=user_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "refunded"

        db.refresh(test_booking)
        assert test_booking.payment_status == PaymentStatus.REFUNDED

    def test_partial_refund(self, client, api_prefix, user_auth_headers, test_booking, db):
        """Should process partial refund"""
        payment_id = self.setup_paid_payment(client, api_prefix, user_auth_headers, test_booking)

        refund_url = f"{api_prefix}/payments/{payment_id}/refund"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            response = client.post(refund_url, json={"payment_id": payment_id, "amount": 25.0}, headers=user_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "partially_refunded"

        db.refresh(test_booking)
        assert test_booking.payment_status == PaymentStatus.PARTIALLY_REFUNDED

    def test_refund_unpaid_payment(self, client, api_prefix, user_auth_headers, test_booking):
        """Should fail to refund a payment that is not PAID"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        refund_url = f"{api_prefix}/payments/{payment_id}/refund"
        response = client.post(refund_url, json={"payment_id": payment_id}, headers=user_auth_headers)
        assert response.status_code == 400

    def test_refund_exceeds_amount(self, client, api_prefix, user_auth_headers, test_booking):
        """Should fail when refund amount exceeds payment amount"""
        payment_id = self.setup_paid_payment(client, api_prefix, user_auth_headers, test_booking)

        refund_url = f"{api_prefix}/payments/{payment_id}/refund"
        response = client.post(refund_url, json={"payment_id": payment_id, "amount": 99999}, headers=user_auth_headers)
        assert response.status_code == 400

    def test_refund_without_auth(self, client, api_prefix):
        """Should fail without authentication"""
        url = f"{api_prefix}/payments/1/refund"
        response = client.post(url, json={"payment_id": 1})
        assert response.status_code == 403

    def test_refund_other_user_payment(self, client, api_prefix, user_auth_headers, admin_auth_headers, test_booking):
        """Should fail to refund another user's payment"""
        payment_id = self.setup_paid_payment(client, api_prefix, user_auth_headers, test_booking)

        refund_url = f"{api_prefix}/payments/{payment_id}/refund"
        response = client.post(refund_url, json={"payment_id": payment_id}, headers=admin_auth_headers)
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.payments
class TestGetPayment:

    def test_get_own_payment(self, client, api_prefix, user_auth_headers, test_booking):
        """Should get own payment by ID"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        get_url = f"{api_prefix}/payments/{payment_id}"
        response = client.get(get_url, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == payment_id
        assert data["data"]["booking_id"] == test_booking.id

    def test_get_other_user_payment(self, client, api_prefix, user_auth_headers, admin_auth_headers, test_booking):
        """Should fail to get another user's payment"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            init_resp = client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)
        payment_id = init_resp.json()["data"]["payment"]["id"]

        get_url = f"{api_prefix}/payments/{payment_id}"
        response = client.get(get_url, headers=admin_auth_headers)
        assert response.status_code == 403

    def test_get_nonexistent_payment(self, client, api_prefix, user_auth_headers):
        """Should fail for non-existent payment"""
        url = f"{api_prefix}/payments/99999"
        response = client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

    def test_get_payment_without_auth(self, client, api_prefix):
        """Should fail without authentication"""
        url = f"{api_prefix}/payments/1"
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.payments
class TestGetPaymentsByBooking:

    def test_get_payments_by_own_booking(self, client, api_prefix, user_auth_headers, test_booking):
        """Should get payments for own booking"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)

        get_url = f"{api_prefix}/payments/booking/{test_booking.id}"
        response = client.get(get_url, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["booking_id"] == test_booking.id

    def test_get_payments_by_other_user_booking(self, client, api_prefix, user_auth_headers, admin_auth_headers, test_booking):
        """Should fail to get payments for another user's booking"""
        get_url = f"{api_prefix}/payments/booking/{test_booking.id}"
        response = client.get(get_url, headers=admin_auth_headers)
        assert response.status_code == 403

    def test_get_payments_nonexistent_booking(self, client, api_prefix, user_auth_headers):
        """Should fail for non-existent booking"""
        url = f"{api_prefix}/payments/booking/99999"
        response = client.get(url, headers=user_auth_headers)
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.payments
class TestListMyPayments:

    def test_list_my_payments(self, client, api_prefix, user_auth_headers, test_booking):
        """Should list user's payments with pagination"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)

        list_url = f"{api_prefix}/payments/"
        response = client.get(list_url, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 1
        assert data["meta"]["total"] >= 1
        assert data["meta"]["page"] == 1

    def test_list_my_payments_with_status_filter(self, client, api_prefix, user_auth_headers, test_booking):
        """Should filter payments by status"""
        init_url = f"{api_prefix}/payments/initiate"
        with patch("app.services.notification_service.NotificationService.create_notification"):
            client.post(init_url, json={
                "booking_id": test_booking.id,
                "payment_method": "credit_card"
            }, headers=user_auth_headers)

        list_url = f"{api_prefix}/payments/?status=pending"
        response = client.get(list_url, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        for payment in data["data"]:
            assert payment["status"] == "pending"

    def test_list_my_payments_empty(self, client, api_prefix, user_auth_headers):
        """Should return empty list when user has no payments"""
        list_url = f"{api_prefix}/payments/"
        response = client.get(list_url, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0
        assert data["meta"]["total"] == 0

    def test_list_my_payments_without_auth(self, client, api_prefix):
        """Should fail without authentication"""
        url = f"{api_prefix}/payments/"
        response = client.get(url)
        assert response.status_code == 403
