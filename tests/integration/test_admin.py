import pytest


@pytest.mark.integration
@pytest.mark.admin
class TestDashboardStats:

    def test_get_dashboard_stats(self, client, admin_url, admin_auth_headers):
        """Admin should get dashboard stats"""
        response = client.get(
            f"{admin_url}/dashboard/stats",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_users" in data["data"]
        assert "total_events" in data["data"]
        assert "total_bookings" in data["data"]
        assert "total_revenue" in data["data"]

    def test_get_dashboard_stats_as_user(self, client, admin_url, user_auth_headers):
        """Regular user should not access dashboard"""
        response = client.get(
            f"{admin_url}/dashboard/stats",
            headers=user_auth_headers
        )
        assert response.status_code == 403

    def test_get_dashboard_stats_without_auth(self, client, admin_url):
        """Should fail without authentication"""
        response = client.get(f"{admin_url}/dashboard/stats")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.admin
class TestUserActivity:

    def test_get_user_activity(self, client, admin_url, admin_auth_headers):
        """Admin should get user activity"""
        response = client.get(
            f"{admin_url}/users/activity",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_users" in data["data"]

    def test_get_user_activity_as_user(self, client, admin_url, user_auth_headers):
        """Regular user should not access user activity"""
        response = client.get(
            f"{admin_url}/users/activity",
            headers=user_auth_headers
        )
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.admin
class TestEventAnalytics:

    def test_get_event_analytics(self, client, admin_url, admin_auth_headers):
        """Admin should get event analytics"""
        response = client.get(
            f"{admin_url}/events/analytics",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_events" in data["data"]

    def test_get_event_analytics_as_user(self, client, admin_url, user_auth_headers):
        """Regular user should not access event analytics"""
        response = client.get(
            f"{admin_url}/events/analytics",
            headers=user_auth_headers
        )
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.admin
class TestBookingReport:

    def test_get_booking_report(self, client, admin_url, admin_auth_headers):
        """Admin should get booking report"""
        response = client.get(
            f"{admin_url}/reports/bookings",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_bookings" in data["data"]

    def test_get_booking_report_with_dates(self, client, admin_url, admin_auth_headers):
        """Should filter booking report by date range"""
        response = client.get(
            f"{admin_url}/reports/bookings?start_date=2024-01-01&end_date=2024-12-31",
            headers=admin_auth_headers
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.admin
class TestRevenueReport:

    def test_get_revenue_report(self, client, admin_url, admin_auth_headers):
        """Admin should get revenue report"""
        response = client.get(
            f"{admin_url}/reports/revenue",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_revenue" in data["data"]

    def test_get_revenue_report_with_period(self, client, admin_url, admin_auth_headers):
        """Should get revenue for specific period"""
        response = client.get(
            f"{admin_url}/reports/revenue?period=this_month",
            headers=admin_auth_headers
        )
        assert response.status_code == 200