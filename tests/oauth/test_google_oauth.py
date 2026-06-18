import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from app.services.oauth_service import GoogleOAuthService
from app.models.user import User
from app.core.enums import UserRole


class TestGoogleOAuthService:
    """Tests for GoogleOAuthService"""

    @pytest.mark.asyncio
    async def test_get_google_user_info_success(self):
        """Test successful Google user info retrieval"""
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {"access_token": "fake_token"}

        mock_userinfo_response = MagicMock()
        mock_userinfo_response.status_code = 200
        mock_userinfo_response.json.return_value = {
            "id": "12345",
            "email": "testuser@gmail.com",
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg"
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_token_response
        mock_client.get.return_value = mock_userinfo_response

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await GoogleOAuthService.get_google_user_info("test_code", "http://localhost/callback")

            assert result["id"] == "12345"
            assert result["email"] == "testuser@gmail.com"
            assert result["given_name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_google_user_info_token_failure(self):
        """Test handling of Google token exchange failure"""
        mock_token_response = MagicMock()
        mock_token_response.status_code = 400
        mock_token_response.text = "Bad request"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_token_response

        from fastapi import HTTPException

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                await GoogleOAuthService.get_google_user_info("bad_code", "http://localhost/callback")
            assert exc.value.status_code == 400

    def test_generate_username_from_email(self):
        """Test username generation from email"""
        username = GoogleOAuthService.generate_username_from_email("john.doe@gmail.com")
        assert username == "john_doe"

        # Test with special characters
        username = GoogleOAuthService.generate_username_from_email("test+user@example.com")
        assert "_" in username

    @pytest.mark.asyncio
    async def test_authenticate_or_create_user_new(self, db):
        """Test creating a new user via Google OAuth"""
        google_data = {
            "id": "google_123",
            "email": "newuser@gmail.com",
            "verified_email": True,
            "given_name": "New",
            "family_name": "User",
            "picture": "https://example.com/pic.jpg"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", new=AsyncMock(return_value=google_data)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(
                db=db,
                code="test_code",
                redirect_uri="http://localhost/callback"
            )

            assert is_new is True
            assert user.email == "newuser@gmail.com"
            assert user.first_name == "New"
            assert user.last_name == "User"
            assert user.oauth_provider == "google"
            assert user.oauth_id == "google_123"
            assert user.is_verified is True
            assert user.role == UserRole.USER

    @pytest.mark.asyncio
    async def test_authenticate_or_create_user_existing_oauth(self, db, test_user):
        """Test authenticating an existing Google OAuth user"""
        test_user.oauth_provider = "google"
        test_user.oauth_id = "google_existing"
        db.commit()

        google_data = {
            "id": "google_existing",
            "email": test_user.email,
            "verified_email": True,
            "given_name": test_user.first_name,
            "family_name": test_user.last_name,
            "picture": test_user.profile_picture
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", new=AsyncMock(return_value=google_data)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(
                db=db,
                code="test_code",
                redirect_uri="http://localhost/callback"
            )

            assert is_new is False
            assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_or_create_user_link_existing(self, db):
        """Test linking Google account to existing email-registered user"""
        from app.utils.auth_utils import hash_password

        existing_user = User(
            username="existing",
            email="existing@gmail.com",
            password_hash=hash_password("Password@123"),
            first_name="Existing",
            last_name="User",
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
            oauth_provider=None,
            oauth_id=None
        )
        db.add(existing_user)
        db.commit()

        google_data = {
            "id": "google_link_123",
            "email": "existing@gmail.com",
            "verified_email": True,
            "given_name": "Existing",
            "family_name": "User",
            "picture": "https://example.com/pic.jpg"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", new=AsyncMock(return_value=google_data)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(
                db=db,
                code="test_code",
                redirect_uri="http://localhost/callback"
            )

            assert is_new is False
            assert user.oauth_provider == "google"
            assert user.oauth_id == "google_link_123"
            assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_authenticate_missing_user_info(self):
        """Test handling of missing user info from Google"""
        google_data = {"id": None, "email": None}

        with patch.object(GoogleOAuthService, "get_google_user_info", new=AsyncMock(return_value=google_data)):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc:
                await GoogleOAuthService.authenticate_or_create_user(
                    db=MagicMock(),
                    code="test_code"
                )
            assert exc.value.status_code == 400


class TestGoogleOAuthEndpoints:
    """Integration tests for Google OAuth endpoints"""

    def test_google_login_redirect(self, client):
        """Test Google login redirects to Google consent screen"""
        from app.core.config import settings

        response = client.get(
            f"{settings.API_PREFIX}/auth/google/login",
            follow_redirects=False
        )
        assert response.status_code in (302, 307)
        assert "accounts.google.com" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_google_callback_success(self, client, db, test_user, api_prefix):
        """Test successful Google OAuth callback"""
        google_data = {
            "id": "google_callback_123",
            "email": test_user.email,
            "verified_email": True,
            "given_name": test_user.first_name,
            "family_name": test_user.last_name,
            "picture": "https://example.com/pic.jpg"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", new=AsyncMock(return_value=google_data)):
            response = client.get(
                f"{api_prefix}/auth/google/callback?code=test_callback_code",
                follow_redirects=False
            )

            # Should redirect to frontend callback URL
            assert response.status_code in (200, 302, 307)

    @pytest.mark.asyncio
    async def test_google_token_exchange_success(self, client, db, test_user, api_prefix):
        """Test successful Google token exchange"""
        google_data = {
            "id": "google_token_123",
            "email": test_user.email,
            "verified_email": True,
            "given_name": test_user.first_name,
            "family_name": test_user.last_name,
            "picture": "https://example.com/pic.jpg"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", new=AsyncMock(return_value=google_data)):
            response = client.post(
                f"{api_prefix}/auth/google/token",
                json={"code": "test_exchange_code"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data["data"]
            assert "refresh_token" in data["data"]
            assert data["data"]["email"] == test_user.email

    def test_google_token_exchange_missing_code(self, client, api_prefix):
        """Test token exchange with missing authorization code"""
        response = client.post(
            f"{api_prefix}/auth/google/token",
            json={"code": ""}
        )

        assert response.status_code == 400

    def test_google_token_exchange_no_code(self, client, api_prefix):
        """Test token exchange without providing code"""
        response = client.post(
            f"{api_prefix}/auth/google/token",
            json={}
        )

        assert response.status_code == 422
