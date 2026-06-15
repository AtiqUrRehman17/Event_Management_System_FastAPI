"""Tests for LinkedIn OAuth authentication flow"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from httpx import Response as HttpxResponse

from app.services.linkedin_oauth_service import LinkedInOAuthService
from app.core.config import settings
from app.core.enums import UserRole


# =============================================================
# Unit Tests: get_login_url
# =============================================================

@pytest.mark.unit
class TestGetLoginUrl:

    def test_returns_valid_url(self):
        """Should return a LinkedIn authorization URL"""
        url = LinkedInOAuthService.get_login_url()
        assert url.startswith("https://www.linkedin.com/oauth/v2/authorization")
        assert "response_type=code" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "openid" in url
        assert "profile" in url
        assert "email" in url

    def test_contains_client_id(self):
        """URL should contain the configured client ID"""
        url = LinkedInOAuthService.get_login_url()
        assert settings.LINKEDIN_CLIENT_ID in url

    def test_contains_redirect_uri(self):
        """URL should contain the configured redirect URI"""
        url = LinkedInOAuthService.get_login_url()
        assert settings.LINKEDIN_REDIRECT_URI in url


# =============================================================
# Unit Tests: generate_username_from_email
# =============================================================

@pytest.mark.unit
class TestGenerateUsernameFromEmail:

    def test_basic_email(self):
        """Standard email should extract part before @"""
        result = LinkedInOAuthService.generate_username_from_email("john.doe@example.com")
        assert result == "john_doe"

    def test_email_with_numbers(self):
        """Email with numbers should keep them"""
        result = LinkedInOAuthService.generate_username_from_email("user123@example.com")
        assert result == "user123"

    def test_email_with_plus(self):
        """Email with + should convert to underscore"""
        result = LinkedInOAuthService.generate_username_from_email("user+tag@example.com")
        assert result == "user_tag"

    def test_email_consecutive_special_chars(self):
        """Consecutive special characters should collapse to single underscore"""
        result = LinkedInOAuthService.generate_username_from_email("user..name@test.com")
        assert result == "user_name"
        assert "__" not in result

    def test_email_leading_trailing_special_chars(self):
        """Leading/trailing special chars should be stripped"""
        result = LinkedInOAuthService.generate_username_from_email("_user_@test.com")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_long_username_truncated(self):
        """Very long email local part should be truncated to 45 chars"""
        long_local = "a" * 100
        result = LinkedInOAuthService.generate_username_from_email(f"{long_local}@example.com")
        assert len(result) <= 45


# =============================================================
# Unit Tests: get_linkedin_user_info (mocked httpx)
# =============================================================

@pytest.mark.unit
class TestGetLinkedinUserInfo:

    @pytest.mark.asyncio
    async def test_successful_token_exchange(self):
        """Should exchange code and return user info with token metadata"""
        mock_userinfo = {
            "sub": "linkedin_123",
            "email": "testuser@example.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg"
        }

        async def mock_post(url, *args, **kwargs):
            return HttpxResponse(200, json={
                "access_token": "mock_access_token",
                "expires_in": 5184000
            })

        async def mock_get(url, *args, **kwargs):
            return HttpxResponse(200, json=mock_userinfo)

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with patch("httpx.AsyncClient.get", side_effect=mock_get):
                result = await LinkedInOAuthService.get_linkedin_user_info("test_code")

        assert result["sub"] == "linkedin_123"
        assert result["email"] == "testuser@example.com"
        assert result["given_name"] == "Test"
        assert result["family_name"] == "User"
        assert result["access_token"] == "mock_access_token"
        assert "expires_at" in result
        assert result["expires_in"] == 5184000

    @pytest.mark.asyncio
    async def test_token_exchange_failure(self):
        """Should raise HTTPException when token exchange fails"""
        async def mock_failed_post(url, *args, **kwargs):
            return HttpxResponse(400, json={"error": "invalid_grant"})

        with patch("httpx.AsyncClient.post", side_effect=mock_failed_post):
            with pytest.raises(HTTPException) as exc:
                await LinkedInOAuthService.get_linkedin_user_info("bad_code")
            assert exc.value.status_code == 400
            assert "Failed to authenticate" in exc.value.detail

    @pytest.mark.asyncio
    async def test_userinfo_failure(self):
        """Should raise HTTPException when userinfo request fails"""
        async def mock_post_response(url, *args, **kwargs):
            return HttpxResponse(200, json={"access_token": "mock_token"})

        async def mock_get_failure(url, *args, **kwargs):
            return HttpxResponse(500, json={"error": "internal"})

        with patch("httpx.AsyncClient.post", side_effect=mock_post_response):
            with patch("httpx.AsyncClient.get", side_effect=mock_get_failure):
                with pytest.raises(HTTPException) as exc:
                    await LinkedInOAuthService.get_linkedin_user_info("test_code")
                assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_access_token_in_response(self):
        """Should raise HTTPException when no access_token returned"""
        async def mock_post_no_token(url, *args, **kwargs):
            return HttpxResponse(200, json={"error": "something_wrong"})

        with patch("httpx.AsyncClient.post", side_effect=mock_post_no_token):
            with pytest.raises(HTTPException) as exc:
                await LinkedInOAuthService.get_linkedin_user_info("test_code")
            assert "No access token" in exc.value.detail

    @pytest.mark.asyncio
    async def test_custom_redirect_uri(self):
        """Should pass custom redirect URI to token endpoint"""
        custom_uri = "http://custom/callback"
        captured_data = {}

        async def mock_post(url, *args, **kwargs):
            nonlocal captured_data
            captured_data = kwargs.get("data", {})
            return HttpxResponse(200, json={"access_token": "mock_token"})

        async def mock_get(url, *args, **kwargs):
            return HttpxResponse(200, json={"sub": "test"})

        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with patch("httpx.AsyncClient.get", side_effect=mock_get):
                await LinkedInOAuthService.get_linkedin_user_info("code", custom_uri)

        assert captured_data.get("redirect_uri") == custom_uri


# =============================================================
# Integration Tests: authenticate_or_create_user
# =============================================================

@pytest.mark.unit
class TestAuthenticateOrCreateUser:

    @pytest.mark.asyncio
    async def test_creates_new_user(self, db):
        """Should create a new user from LinkedIn info when none exists"""
        mock_data = {
            "sub": "linkedin_456",
            "email": "newlinkedinuser@example.com",
            "email_verified": True,
            "given_name": "New",
            "family_name": "LinkedInUser",
            "picture": "https://example.com/pic.jpg",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.email == "newlinkedinuser@example.com"
        assert user.oauth_provider == "linkedin"
        assert user.oauth_id == "linkedin_456"
        assert user.is_verified is True
        assert user.role == UserRole.USER
        assert user.first_name == "New"
        assert user.last_name == "LinkedInUser"
        assert token_info["access_token"] == "mock_at"

    @pytest.mark.asyncio
    async def test_finds_existing_oauth_user(self, db, test_user):
        """Should return existing user found by OAuth provider + sub"""
        test_user.oauth_provider = "linkedin"
        test_user.oauth_id = "existing_linkedin_id"
        db.commit()

        mock_data = {
            "sub": "existing_linkedin_id",
            "email": test_user.email,
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_links_to_existing_email_user(self, db, test_user):
        """Should link LinkedIn OAuth to existing user found by email"""
        mock_data = {
            "sub": "link_linkedin_id",
            "email": test_user.email,
            "email_verified": True,
            "given_name": "Updated",
            "family_name": "Name",
            "picture": "https://example.com/pic.jpg",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.id == test_user.id
        assert user.oauth_provider == "linkedin"
        assert user.oauth_id == "link_linkedin_id"
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_updates_existing_user_profile(self, db, test_user):
        """Should update name and picture for existing OAuth user"""
        test_user.oauth_provider = "linkedin"
        test_user.oauth_id = "update_profile_id"
        test_user.first_name = "Old"
        test_user.last_name = "Name"
        test_user.profile_picture = "https://old.example.com/pic.jpg"
        db.commit()

        mock_data = {
            "sub": "update_profile_id",
            "email": test_user.email,
            "email_verified": True,
            "given_name": "New",
            "family_name": "Updated",
            "picture": "https://new.example.com/pic.jpg",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.first_name == "New"
        assert user.last_name == "Updated"
        assert user.profile_picture == "https://new.example.com/pic.jpg"

    @pytest.mark.asyncio
    async def test_raises_on_missing_sub(self, db):
        """Should raise when LinkedIn returns no sub (user ID)"""
        mock_data = {
            "email": "nosub@example.com",
            "given_name": "No",
            "family_name": "Sub",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            with pytest.raises(HTTPException) as exc:
                await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")
            assert exc.value.status_code == 400
            assert "Insufficient user info" in exc.value.detail

    @pytest.mark.asyncio
    async def test_creates_user_without_email(self, db):
        """Should create user even when LinkedIn doesn't provide email"""
        mock_data = {
            "sub": "no_email_linkedin",
            "given_name": "NoEmail",
            "family_name": "User",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.oauth_id == "no_email_linkedin"
        assert user.email.endswith("@linkedin.user")
        assert user.first_name == "NoEmail"

    @pytest.mark.asyncio
    async def test_uses_preferred_username(self, db):
        """Should use preferred_username when available"""
        mock_data = {
            "sub": "pref_user_id",
            "email": "preferred@example.com",
            "email_verified": True,
            "given_name": "Preferred",
            "family_name": "User",
            "preferred_username": "my_custom_handle",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.username == "my_custom_handle"

    @pytest.mark.asyncio
    async def test_generates_unique_username(self, db, test_user):
        """Should generate unique username when base name exists"""
        mock_data = {
            "sub": "unique_un_id",
            "email": "testuser@example.com",  # Same as test_user's email local part
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.username.startswith("testuser")
        assert user.username != "testuser"

    @pytest.mark.asyncio
    async def test_new_user_has_random_password(self, db):
        """New OAuth user should have a hashed password (not plaintext)"""
        mock_data = {
            "sub": "check_pw_linkedin",
            "email": "checkpw@example.com",
            "email_verified": True,
            "given_name": "Check",
            "family_name": "Pw",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.password_hash is not None
        assert user.password_hash != ""
        assert user.password_hash != user.email

    @pytest.mark.asyncio
    async def test_does_not_update_email_if_taken(self, db, test_user, test_admin):
        """Should not update email to one already used by another user"""
        test_user.oauth_provider = "linkedin"
        test_user.oauth_id = "email_conflict_id"
        test_user.email = "original@example.com"
        db.commit()

        mock_data = {
            "sub": "email_conflict_id",
            "email": test_admin.email,  # Taken by another user
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.email == "original@example.com"

    @pytest.mark.asyncio
    async def test_token_info_returned(self, db):
        """Should return token info dict with access_token and expiry"""
        mock_data = {
            "sub": "token_info_test",
            "email": "tokeninfo@example.com",
            "email_verified": True,
            "given_name": "Token",
            "family_name": "Info",
            "picture": None,
            "access_token": "returned_access_token",
            "expires_in": 3600
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await LinkedInOAuthService.authenticate_or_create_user(db, "test_code")

        assert token_info["access_token"] == "returned_access_token"
        assert token_info["expires_in"] == 3600
        assert "expires_at" in token_info


# =============================================================
# API Integration Tests (via test client)
# =============================================================

@pytest.mark.integration
class TestLinkedInOAuthAPIEndpoints:

    def test_linkedin_login_redirects(self, client, auth_url):
        """GET /api/v1/auth/linkedin/login should redirect to LinkedIn"""
        response = client.get(f"{auth_url}/linkedin/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers.get("location", "")
        assert "linkedin.com" in location

    def test_linkedin_callback_missing_code(self, client, auth_url):
        """GET /api/v1/auth/linkedin/callback without code should return 422"""
        response = client.get(f"{auth_url}/linkedin/callback", follow_redirects=False)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_linkedin_callback_with_mocked_auth(self, client, auth_url, db):
        """GET /api/v1/auth/linkedin/callback with mocked OAuth should redirect to frontend"""
        from app.dependencies.db import get_db

        mock_data = {
            "sub": "callback_linkedin_id",
            "email": "linkedincallback@example.com",
            "email_verified": True,
            "given_name": "Callback",
            "family_name": "User",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.get(
                f"{auth_url}/linkedin/callback?code=mocked_code",
                follow_redirects=False
            )
            app.dependency_overrides.clear()

        assert response.status_code in (302, 307)
        location = response.headers.get("location", "")
        assert settings.FRONTEND_URL in location
        assert "access_token" in location

    @pytest.mark.asyncio
    async def test_linkedin_token_exchange_new_user(self, client, auth_url, db):
        """POST /api/v1/auth/linkedin/token should return JWT tokens for new user"""
        from app.dependencies.db import get_db

        mock_data = {
            "sub": "token_exchange_linkedin",
            "email": "linkedintoken@example.com",
            "email_verified": True,
            "given_name": "Token",
            "family_name": "Exchange",
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/linkedin/token",
                json={"code": "mocked_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["is_new_user"] is True
        assert data["data"]["email"] == "linkedintoken@example.com"

    @pytest.mark.asyncio
    async def test_linkedin_token_exchange_existing_user(self, client, auth_url, db, test_user):
        """POST /api/v1/auth/linkedin/token should return JWT for existing user linking"""
        from app.dependencies.db import get_db

        mock_data = {
            "sub": "link_existing_linkedin",
            "email": test_user.email,
            "email_verified": True,
            "given_name": test_user.first_name,
            "family_name": test_user.last_name,
            "picture": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(LinkedInOAuthService, "get_linkedin_user_info", AsyncMock(return_value=mock_data)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/linkedin/token",
                json={"code": "mocked_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_new_user"] is False
        assert data["data"]["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_linkedin_token_exchange_failure(self, client, auth_url, db):
        """POST /api/v1/auth/linkedin/token should return 400 on OAuth failure"""
        from app.dependencies.db import get_db

        with patch.object(
            LinkedInOAuthService, "get_linkedin_user_info",
            AsyncMock(side_effect=HTTPException(status_code=400, detail="LinkedIn authentication failed"))
        ):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/linkedin/token",
                json={"code": "bad_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_linkedin_token_exchange_no_code(self, client, auth_url):
        """POST /api/v1/auth/linkedin/token without code should return 422"""
        response = client.post(f"{auth_url}/linkedin/token", json={})
        assert response.status_code == 422
