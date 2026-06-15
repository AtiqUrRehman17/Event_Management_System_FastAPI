"""Tests for Google OAuth authentication flow"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from httpx import Response as HttpxResponse

from app.services.oauth_service import GoogleOAuthService
from app.core.config import settings
from app.core.enums import UserRole


# =============================================================
# Unit Tests: generate_username_from_email
# =============================================================

@pytest.mark.unit
class TestGenerateUsernameFromEmail:

    def test_basic_email(self):
        """Standard email should extract part before @"""
        result = GoogleOAuthService.generate_username_from_email("john.doe@gmail.com")
        assert result == "john_doe"

    def test_email_with_numbers(self):
        """Email with numbers should keep them"""
        result = GoogleOAuthService.generate_username_from_email("user123@example.com")
        assert result == "user123"

    def test_email_with_plus(self):
        """Email with + should convert + to underscore"""
        result = GoogleOAuthService.generate_username_from_email("user+tag@example.com")
        assert result == "user_tag"

    def test_email_with_dots_only(self):
        """Multiple dots should become single underscores"""
        result = GoogleOAuthService.generate_username_from_email("a.b.c.d@test.com")
        assert result == "a_b_c_d"

    def test_email_special_chars_replaced(self):
        """Special characters should be replaced with underscore"""
        result = GoogleOAuthService.generate_username_from_email("user-name!test@domain.com")
        assert result == "user_name_test"

    def test_long_username_truncated(self):
        """Very long email local part should be truncated to 45 chars"""
        long_local = "a" * 100
        result = GoogleOAuthService.generate_username_from_email(f"{long_local}@example.com")
        assert len(result) <= 45


# =============================================================
# Unit Tests: get_google_user_info (mocked httpx)
# =============================================================

@pytest.mark.unit
class TestGetGoogleUserInfo:

    @pytest.mark.asyncio
    async def test_successful_token_exchange(self):
        """Should exchange code and return user info"""
        mock_userinfo = {
            "id": "12345",
            "email": "testuser@gmail.com",
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg"
        }

        async def mock_post(url, *args, **kwargs):
            if "token" in url:
                return HttpxResponse(200, json={"access_token": "mock_access_token"})
            return HttpxResponse(200, json=mock_userinfo)

        async def mock_get(url, *args, **kwargs):
            return HttpxResponse(200, json=mock_userinfo)

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with patch("httpx.AsyncClient.get", side_effect=mock_get):
                result = await GoogleOAuthService.get_google_user_info("test_code")

        assert result["id"] == "12345"
        assert result["email"] == "testuser@gmail.com"
        assert result["given_name"] == "Test"
        assert result["family_name"] == "User"
        assert result["verified_email"] is True

    @pytest.mark.asyncio
    async def test_token_exchange_failure(self):
        """Should raise HTTPException when token exchange fails"""
        async def mock_failed_post(url, *args, **kwargs):
            return HttpxResponse(400, json={"error": "invalid_grant"})

        with patch("httpx.AsyncClient.post", side_effect=mock_failed_post):
            with pytest.raises(HTTPException) as exc:
                await GoogleOAuthService.get_google_user_info("bad_code")
            assert exc.value.status_code == 400
            assert "Failed to authenticate" in exc.value.detail

    @pytest.mark.asyncio
    async def test_userinfo_failure(self):
        """Should raise HTTPException when userinfo request fails"""
        async def mock_post_response(url, *args, **kwargs):
            if "token" in url:
                return HttpxResponse(200, json={"access_token": "mock_token"})
            return HttpxResponse(200, json={})

        async def mock_get_failure(url, *args, **kwargs):
            return HttpxResponse(500, json={"error": "internal"})

        with patch("httpx.AsyncClient.post", side_effect=mock_post_response):
            with patch("httpx.AsyncClient.get", side_effect=mock_get_failure):
                with pytest.raises(HTTPException) as exc:
                    await GoogleOAuthService.get_google_user_info("test_code")
                assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_access_token_in_response(self):
        """Should raise HTTPException when no access_token returned"""
        async def mock_post_no_token(url, *args, **kwargs):
            return HttpxResponse(200, json={"error": "something_wrong"})

        with patch("httpx.AsyncClient.post", side_effect=mock_post_no_token):
            with pytest.raises(HTTPException) as exc:
                await GoogleOAuthService.get_google_user_info("test_code")
            assert "No access token" in exc.value.detail


# =============================================================
# Integration Tests: authenticate_or_create_user
# =============================================================

@pytest.mark.unit
class TestAuthenticateOrCreateUser:

    @pytest.mark.asyncio
    async def test_creates_new_user(self, db):
        """Should create a new user from Google info when none exists"""
        mock_userinfo = {
            "id": "google_123",
            "email": "newgoogleuser@gmail.com",
            "verified_email": True,
            "given_name": "New",
            "family_name": "GoogleUser",
            "picture": "https://example.com/pic.jpg"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.email == "newgoogleuser@gmail.com"
        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_123"
        assert user.is_verified is True
        assert user.is_active is True
        assert user.role == UserRole.USER
        assert user.first_name == "New"
        assert user.last_name == "GoogleUser"

    @pytest.mark.asyncio
    async def test_finds_existing_oauth_user(self, db, test_user):
        """Should return existing user found by OAuth provider + id"""
        from app.models.user import User

        test_user.oauth_provider = "google"
        test_user.oauth_id = "existing_google_id"
        db.commit()

        mock_userinfo = {
            "id": "existing_google_id",
            "email": test_user.email,
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": None
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.id == test_user.id
        assert user.oauth_id == "existing_google_id"

    @pytest.mark.asyncio
    async def test_links_to_existing_email_user(self, db, test_user):
        """Should link Google OAuth to existing user found by email"""
        mock_userinfo = {
            "id": "new_google_link_id",
            "email": test_user.email,  # Same email as existing user
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/pic.jpg"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.id == test_user.id
        assert user.oauth_provider == "google"
        assert user.oauth_id == "new_google_link_id"
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_creates_user_with_unique_username(self, db, test_user):
        """Should generate a unique username when base name exists"""
        mock_userinfo = {
            "id": "unique_test_id",
            "email": "testuser@gmail.com",  # Same local part as test_user's username
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": None
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.username != "testuser"  # Should have a suffix
        assert user.username.startswith("testuser")

    @pytest.mark.asyncio
    async def test_raises_on_missing_google_id(self, db):
        """Should raise when Google returns no id"""
        mock_userinfo = {
            "email": "noid@example.com",
            "given_name": "No",
            "family_name": "Id"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            with pytest.raises(HTTPException) as exc:
                await GoogleOAuthService.authenticate_or_create_user(db, "test_code")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_on_missing_email(self, db):
        """Should raise when Google returns no email"""
        mock_userinfo = {
            "id": "no_email_id",
            "given_name": "No",
            "family_name": "Email"
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            with pytest.raises(HTTPException) as exc:
                await GoogleOAuthService.authenticate_or_create_user(db, "test_code")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_updates_profile_picture_for_existing_user(self, db, test_user):
        """Should update profile picture when Google returns a different one"""
        test_user.oauth_provider = "google"
        test_user.oauth_id = "pic_update_id"
        test_user.profile_picture = "https://old.example.com/pic.jpg"
        db.commit()

        new_picture = "https://new.example.com/pic.jpg"
        mock_userinfo = {
            "id": "pic_update_id",
            "email": test_user.email,
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": new_picture
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.profile_picture == new_picture

    @pytest.mark.asyncio
    async def test_new_user_has_random_password(self, db):
        """New OAuth user should have a hashed password (not plaintext)"""
        mock_userinfo = {
            "id": "check_pw_id",
            "email": "checkpw@gmail.com",
            "verified_email": True,
            "given_name": "Check",
            "family_name": "Pw",
            "picture": None
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            user, is_new = await GoogleOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.password_hash is not None
        assert user.password_hash != ""
        assert user.password_hash != user.email  # Not plaintext


# =============================================================
# API Integration Tests (via test client)
# =============================================================

@pytest.mark.integration
class TestGoogleOAuthAPIEndpoints:

    def test_google_login_redirects(self, client, auth_url):
        """GET /api/v1/auth/google/login should redirect to Google"""
        response = client.get(f"{auth_url}/google/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "accounts.google.com" in response.headers.get("location", "")

    def test_google_callback_missing_code(self, client, auth_url):
        """GET /api/v1/auth/google/callback without code should fail"""
        response = client.get(f"{auth_url}/google/callback", follow_redirects=False)
        # FastAPI will return 422 for missing required query param
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_google_callback_with_mocked_auth(self, client, auth_url, db):
        """GET /api/v1/auth/google/callback with mocked OAuth should redirect to frontend"""
        from app.dependencies.db import get_db

        mock_userinfo = {
            "id": "callback_test_id",
            "email": "callbackuser@gmail.com",
            "verified_email": True,
            "given_name": "Callback",
            "family_name": "User",
            "picture": None
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            # Override db dependency
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.get(
                f"{auth_url}/google/callback?code=mocked_auth_code",
                follow_redirects=False
            )
            app.dependency_overrides.clear()

        assert response.status_code in (302, 307)
        location = response.headers.get("location", "")
        assert settings.FRONTEND_URL in location
        assert "access_token" in location

    @pytest.mark.asyncio
    async def test_google_token_exchange_new_user(self, client, auth_url, db):
        """POST /api/v1/auth/google/token should return JWT tokens for new user"""
        from app.dependencies.db import get_db

        mock_userinfo = {
            "id": "token_exchange_id",
            "email": "tokentest@gmail.com",
            "verified_email": True,
            "given_name": "Token",
            "family_name": "Test",
            "picture": None
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/google/token",
                json={"code": "mocked_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["is_new_user"] is True
        assert data["data"]["email"] == "tokentest@gmail.com"

    @pytest.mark.asyncio
    async def test_google_token_exchange_existing_user(self, client, auth_url, db, test_user):
        """POST /api/v1/auth/google/token should return JWT for existing user linking"""
        from app.dependencies.db import get_db

        mock_userinfo = {
            "id": "link_existing_id",
            "email": test_user.email,  # Same email as test_user
            "verified_email": True,
            "given_name": test_user.first_name,
            "family_name": test_user.last_name,
            "picture": None
        }

        with patch.object(GoogleOAuthService, "get_google_user_info", AsyncMock(return_value=mock_userinfo)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/google/token",
                json={"code": "mocked_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_new_user"] is False
        assert data["data"]["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_google_token_exchange_failure(self, client, auth_url, db):
        """POST /api/v1/auth/google/token should return 400 on OAuth failure"""
        from app.dependencies.db import get_db

        with patch.object(
            GoogleOAuthService, "get_google_user_info",
            AsyncMock(side_effect=HTTPException(status_code=400, detail="Google authentication failed"))
        ):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/google/token",
                json={"code": "bad_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_google_token_exchange_no_code(self, client, auth_url):
        """POST /api/v1/auth/google/token without code should return 422"""
        response = client.post(f"{auth_url}/google/token", json={})
        assert response.status_code == 422
