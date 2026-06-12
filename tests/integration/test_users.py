import pytest


@pytest.mark.integration
@pytest.mark.users
class TestGetMyProfile:

    def test_get_profile_success(self, client, users_url, user_auth_headers, test_user):
        """Should return current user profile"""
        response = client.get(f"{users_url}/me", headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "testuser"
        assert data["data"]["email"] == "testuser@example.com"

    def test_get_profile_without_token(self, client, users_url):
        """Should fail without auth token"""
        response = client.get(f"{users_url}/me")
        assert response.status_code == 403

    def test_get_profile_no_password_in_response(self, client, users_url, user_auth_headers):
        """Password should never be in profile response"""
        response = client.get(f"{users_url}/me", headers=user_auth_headers)
        data = response.json()
        assert "password" not in data["data"]
        assert "password_hash" not in data["data"]

    def test_get_profile_contains_required_fields(self, client, users_url, user_auth_headers):
        """Profile should contain all required fields"""
        response = client.get(f"{users_url}/me", headers=user_auth_headers)
        data = response.json()["data"]
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "role" in data
        assert "is_active" in data


@pytest.mark.integration
@pytest.mark.users
class TestUpdateProfile:

    def test_update_profile_success(self, client, users_url, user_auth_headers):
        """Should update profile successfully"""
        response = client.put(f"{users_url}/me", json={
            "first_name": "Updated",
            "last_name": "Name"
        }, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["first_name"] == "Updated"

    def test_update_bio(self, client, users_url, user_auth_headers):
        """Should update bio successfully"""
        response = client.put(f"{users_url}/me", json={
            "bio": "This is my test bio"
        }, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["bio"] == "This is my test bio"

    def test_update_phone(self, client, users_url, user_auth_headers):
        """Should update phone successfully"""
        response = client.put(f"{users_url}/me", json={
            "phone": "+1234567890"
        }, headers=user_auth_headers)
        assert response.status_code == 200

    def test_update_with_duplicate_email(self, client, users_url, user_auth_headers, test_admin):
        """Should fail when updating to existing email"""
        response = client.put(f"{users_url}/me", json={
            "email": "testadmin@example.com"  # Admin's email
        }, headers=user_auth_headers)
        assert response.status_code == 400

    def test_update_without_token(self, client, users_url):
        """Should fail without auth token"""
        response = client.put(f"{users_url}/me", json={
            "first_name": "Updated"
        })
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.users
class TestChangePassword:

    def test_change_password_success(self, client, users_url, user_auth_headers):
        """Should change password successfully"""
        response = client.post(f"{users_url}/me/change-password", json={
            "current_password": "TestPass@123",
            "new_password": "NewPass@456",
            "confirm_password": "NewPass@456"
        }, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_change_password_wrong_current(self, client, users_url, user_auth_headers):
        """Should fail with wrong current password"""
        response = client.post(f"{users_url}/me/change-password", json={
            "current_password": "WrongPass@123",
            "new_password": "NewPass@456",
            "confirm_password": "NewPass@456"
        }, headers=user_auth_headers)
        assert response.status_code == 401

    def test_change_password_mismatch(self, client, users_url, user_auth_headers):
        """Should fail when passwords don't match"""
        response = client.post(f"{users_url}/me/change-password", json={
            "current_password": "TestPass@123",
            "new_password": "NewPass@456",
            "confirm_password": "DifferentPass@456"
        }, headers=user_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_change_password_without_token(self, client, users_url):
        """Should fail without auth token"""
        response = client.post(f"{users_url}/me/change-password", json={
            "current_password": "TestPass@123",
            "new_password": "NewPass@456",
            "confirm_password": "NewPass@456"
        })
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.users
class TestAdminUserManagement:

    def test_get_all_users_as_admin(self, client, users_url, admin_auth_headers, test_user):
        """Admin should get all users"""
        response = client.get(f"{users_url}/", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_all_users_as_user(self, client, users_url, user_auth_headers):
        """Regular user should not access all users"""
        response = client.get(f"{users_url}/", headers=user_auth_headers)
        assert response.status_code == 403

    def test_get_user_by_id_as_admin(self, client, users_url, admin_auth_headers, test_user):
        """Admin should get user by ID"""
        response = client.get(
            f"{users_url}/{test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_user.id

    def test_deactivate_user(self, client, users_url, admin_auth_headers, test_user):
        """Admin should deactivate a user"""
        response = client.put(
            f"{users_url}/{test_user.id}/deactivate",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_active"] is False

    def test_activate_user(self, client, users_url, admin_auth_headers, inactive_user):
        """Admin should activate a user"""
        response = client.put(
            f"{users_url}/{inactive_user.id}/activate",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_active"] is True

    def test_get_nonexistent_user(self, client, users_url, admin_auth_headers):
        """Should return 404 for non-existent user"""
        response = client.get(
            f"{users_url}/99999",
            headers=admin_auth_headers
        )
        assert response.status_code == 404