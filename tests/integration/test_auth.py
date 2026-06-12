import pytest
from unittest.mock import patch


@pytest.mark.integration
@pytest.mark.auth
class TestRegister:

    def test_register_success(self, client, auth_url):
        """Should register a new user successfully"""
        response = client.post(f"{auth_url}/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass@123",
            "first_name": "New",
            "last_name": "User"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "newuser" in data["data"]["user"]["username"]

    def test_register_duplicate_email(self, client, auth_url, test_user):
        """Should fail with duplicate email"""
        response = client.post(f"{auth_url}/register", json={
            "username": "anotheruser",
            "email": "testuser@example.com",  # Already exists
            "password": "NewPass@123",
            "first_name": "Another",
            "last_name": "User"
        })
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_register_duplicate_username(self, client, auth_url, test_user):
        """Should fail with duplicate username"""
        response = client.post(f"{auth_url}/register", json={
            "username": "testuser",  # Already exists
            "email": "different@example.com",
            "password": "NewPass@123",
            "first_name": "Test",
            "last_name": "User"
        })
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_register_invalid_email(self, client, auth_url):
        """Should fail with invalid email"""
        response = client.post(f"{auth_url}/register", json={
            "username": "newuser",
            "email": "not-an-email",
            "password": "NewPass@123",
            "first_name": "New",
            "last_name": "User"
        })
        assert response.status_code == 422

    def test_register_weak_password(self, client, auth_url):
        """Should fail with weak password"""
        response = client.post(f"{auth_url}/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "weak",
            "first_name": "New",
            "last_name": "User"
        })
        assert response.status_code == 422

    def test_register_missing_fields(self, client, auth_url):
        """Should fail with missing required fields"""
        response = client.post(f"{auth_url}/register", json={
            "username": "newuser"
        })
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.auth
class TestLogin:

    def test_login_success(self, client, auth_url, test_user):
        """Should login successfully with valid credentials"""
        response = client.post(f"{auth_url}/login", json={
            "username": "testuser",
            "password": "TestPass@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_login_wrong_password(self, client, auth_url, test_user):
        """Should fail with wrong password"""
        response = client.post(f"{auth_url}/login", json={
            "username": "testuser",
            "password": "WrongPass@123"
        })
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False

    def test_login_wrong_username(self, client, auth_url):
        """Should fail with non-existent username"""
        response = client.post(f"{auth_url}/login", json={
            "username": "nonexistent",
            "password": "TestPass@123"
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, client, auth_url, inactive_user):
        """Should fail for inactive user"""
        response = client.post(f"{auth_url}/login", json={
            "username": "inactiveuser",
            "password": "TestPass@123"
        })
        assert response.status_code == 401

    def test_login_returns_user_info(self, client, auth_url, test_user):
        """Login response should contain user info"""
        response = client.post(f"{auth_url}/login", json={
            "username": "testuser",
            "password": "TestPass@123"
        })
        data = response.json()
        user = data["data"]["user"]
        assert user["username"] == "testuser"
        assert user["email"] == "testuser@example.com"
        assert "password" not in user
        assert "password_hash" not in user

    def test_login_missing_fields(self, client, auth_url):
        """Should fail with missing fields"""
        response = client.post(f"{auth_url}/login", json={
            "username": "testuser"
        })
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.auth
class TestLogout:

    def test_logout_success(self, client, auth_url, test_user, user_auth_headers, user_refresh_token):
        """Should logout successfully"""
        response = client.post(
            f"{auth_url}/logout",
            json={"refresh_token": user_refresh_token},
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_logout_without_token(self, client, auth_url):
        """Should fail without auth token"""
        response = client.post(f"{auth_url}/logout")
        assert response.status_code == 403

    def test_logout_blacklists_token(self, client, auth_url, test_user, user_auth_headers, user_refresh_token):
        """After logout, token should be blacklisted"""
        # Logout first
        client.post(
            f"{auth_url}/logout",
            json={"refresh_token": user_refresh_token},
            headers=user_auth_headers
        )

        # Try using the same token again
        response = client.post(
            f"{auth_url}/logout",
            headers=user_auth_headers
        )
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
class TestRefreshToken:

    def test_refresh_token_success(self, client, auth_url, user_refresh_token):
        """Should return new tokens with valid refresh token"""
        response = client.post(f"{auth_url}/refresh", json={
            "refresh_token": user_refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_refresh_with_invalid_token(self, client, auth_url):
        """Should fail with invalid refresh token"""
        response = client.post(f"{auth_url}/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        assert response.status_code == 401

    def test_refresh_with_access_token(self, client, auth_url, user_token):
        """Should fail when using access token as refresh token"""
        response = client.post(f"{auth_url}/refresh", json={
            "refresh_token": user_token
        })
        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.auth
class TestForgotPassword:

    def test_forgot_password_success(self, client, auth_url, test_user):
        """Should return success even for valid email"""
        with patch("app.services.email_service.EmailService.send_email", return_value=True):
            response = client.post(f"{auth_url}/forgot-password", json={
                "email": "testuser@example.com"
            })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_forgot_password_unknown_email(self, client, auth_url):
        """Should return success even for unknown email (security)"""
        response = client.post(f"{auth_url}/forgot-password", json={
            "email": "unknown@example.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_forgot_password_invalid_email(self, client, auth_url):
        """Should fail with invalid email format"""
        response = client.post(f"{auth_url}/forgot-password", json={
            "email": "not-an-email"
        })
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.auth
class TestResetPassword:

    def test_reset_password_invalid_token(self, client, auth_url):
        """Should fail with invalid token"""
        response = client.post(f"{auth_url}/reset-password", json={
            "token": "invalid-token",
            "new_password": "NewPass@123",
            "confirm_password": "NewPass@123"
        })
        assert response.status_code == 401

    def test_reset_password_mismatch(self, client, auth_url):
        """Should fail when passwords don't match"""
        response = client.post(f"{auth_url}/reset-password", json={
            "token": "some-token",
            "new_password": "NewPass@123",
            "confirm_password": "DifferentPass@123"
        })
        assert response.status_code == 422

    def test_reset_password_weak_password(self, client, auth_url):
        """Should fail with weak password"""
        response = client.post(f"{auth_url}/reset-password", json={
            "token": "some-token",
            "new_password": "weak",
            "confirm_password": "weak"
        })
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.auth
class TestEmailVerification:

    def test_verify_invalid_token(self, client, auth_url):
        """Should fail with invalid verification token"""
        response = client.post(f"{auth_url}/verify-email", json={
            "token": "invalid-token"
        })
        assert response.status_code == 401

    def test_verify_via_get(self, client, auth_url):
        """GET verify email should fail with invalid token"""
        response = client.get(f"{auth_url}/verify-email?token=invalid-token")
        assert response.status_code == 401

    def test_resend_verification_unknown_email(self, client, auth_url):
        """Should return success for unknown email (security)"""
        response = client.post(f"{auth_url}/resend-verification", json={
            "email": "unknown@example.com"
        })
        assert response.status_code == 200

    def test_resend_verification_already_verified(self, client, auth_url, test_user):
        """Should return success for already verified user"""
        response = client.post(f"{auth_url}/resend-verification", json={
            "email": "testuser@example.com"
        })
        assert response.status_code == 200