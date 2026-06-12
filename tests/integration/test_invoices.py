import pytest


@pytest.mark.integration
@pytest.mark.invoices
class TestGetInvoice:

    def test_get_invoice_json_success(self, client, invoices_url, user_auth_headers, test_booking):
        """Should return invoice data as JSON"""
        response = client.get(
            f"{invoices_url}/{test_booking.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "invoice_number" in data["data"]
        assert "total_amount" in data["data"]

    def test_get_invoice_with_tax(self, client, invoices_url, user_auth_headers, test_booking):
        """Should calculate tax correctly"""
        response = client.get(
            f"{invoices_url}/{test_booking.id}?tax_rate=10",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tax_rate"] == 10.0
        assert data["data"]["tax_amount"] > 0

    def test_get_invoice_without_auth(self, client, invoices_url, test_booking):
        """Should fail without authentication"""
        response = client.get(f"{invoices_url}/{test_booking.id}")
        assert response.status_code == 403

    def test_get_invoice_nonexistent_booking(self, client, invoices_url, user_auth_headers):
        """Should return 404 for non-existent booking"""
        response = client.get(
            f"{invoices_url}/99999",
            headers=user_auth_headers
        )
        assert response.status_code == 404

    def test_admin_can_get_any_invoice(self, client, invoices_url, admin_auth_headers, test_booking):
        """Admin should get any booking's invoice"""
        response = client.get(
            f"{invoices_url}/{test_booking.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    def test_invoice_number_generated(self, client, invoices_url, user_auth_headers, test_booking, db):
        """Invoice number should be generated on first access"""
        client.get(
            f"{invoices_url}/{test_booking.id}",
            headers=user_auth_headers
        )
        db.refresh(test_booking)
        assert test_booking.invoice_number is not None
        assert test_booking.invoice_number.startswith("INV-")


@pytest.mark.integration
@pytest.mark.invoices
class TestUpdatePaymentStatus:

    def test_update_payment_status_as_admin(self, client, invoices_url, admin_auth_headers, test_booking):
        """Admin should update payment status"""
        response = client.post(
            f"{invoices_url}/{test_booking.id}/payment?payment_status=paid&payment_method=credit_card",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["payment_status"] == "paid"

    def test_update_payment_status_as_user(self, client, invoices_url, user_auth_headers, test_booking):
        """Regular user should not update payment status"""
        response = client.post(
            f"{invoices_url}/{test_booking.id}/payment?payment_status=paid",
            headers=user_auth_headers
        )
        assert response.status_code == 403