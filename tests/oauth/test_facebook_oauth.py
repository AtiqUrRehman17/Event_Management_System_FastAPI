"""Tests for Facebook OAuth authentication flow"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from httpx import Response as HttpxResponse

from app.services.facebook_oauth_service import FacebookOAuthService
from app.core.config import settings
from app.core.enums import UserRole


# =============================================================
# Unit Tests: get_login_url
# =============================================================

@pytest.mark.unit
class TestGetLoginUrl:

    def test_returns_valid_url(self):
        """Should return a Facebook authorization URL"""
        url = FacebookOAuthService.get_login_url()
        assert url.startswith("https://www.facebook.com/v18.0/dialog/oauth")
        assert "response_type=code" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=" in url
        assert "public_profile" in url
        assert "email" in url

    def test_contains_client_id(self):
        """URL should contain the configured client ID"""
        url = FacebookOAuthService.get_login_url()
        assert settings.FACEBOOK_CLIENT_ID in url

    def test_contains_redirect_uri(self):
        """URL should contain the configured redirect URI"""
        url = FacebookOAuthService.get_login_url()
        assert settings.FACEBOOK_REDIRECT_URI in url


# =============================================================
# Unit Tests: generate_username_from_email
# =============================================================

@pytest.mark.unit
class TestGenerateUsernameFromEmail:

    def test_basic_email(self):
        """Standard email should extract part before @"""
        result = FacebookOAuthService.generate_username_from_email("john.doe@example.com")
        assert result == "john_doe"

    def test_email_with_numbers(self):
        """Email with numbers should keep them"""
        result = FacebookOAuthService.generate_username_from_email("user123@example.com")
        assert result == "user123"

    def test_email_with_plus(self):
        """Email with + should convert to underscore"""
        result = FacebookOAuthService.generate_username_from_email("user+tag@example.com")
        assert result == "user_tag"

    def test_email_consecutive_special_chars(self):
        """Consecutive special characters should collapse to single underscore"""
        result = FacebookOAuthService.generate_username_from_email("user..name@test.com")
        assert result == "user_name"
        assert "__" not in result

    def test_email_leading_trailing_special_chars(self):
        """Leading/trailing special chars should be stripped"""
        result = FacebookOAuthService.generate_username_from_email("_user_@test.com")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_long_username_truncated(self):
        """Very long email local part should be truncated to 45 chars"""
        long_local = "a" * 100
        result = FacebookOAuthService.generate_username_from_email(f"{long_local}@example.com")
        assert len(result) <= 45

    def test_none_for_empty_email(self):
        """Empty email should return None"""
        result = FacebookOAuthService.generate_username_from_email("")
        assert result is None

    def test_none_for_none_email(self):
        """None email should return None"""
        result = FacebookOAuthService.generate_username_from_email(None)
        assert result is None


# =============================================================
# Unit Tests: get_facebook_user_info (mocked httpx)
# =============================================================

@pytest.mark.unit
class TestGetFacebookUserInfo:

    @pytest.mark.asyncio
    async def test_successful_token_exchange(self):
        """Should exchange code and return user info with picture"""
        mock_userinfo = {
            "id": "fb_123",
            "email": "testuser@example.com",
            "first_name": "Test",
            "last_name": "User",
            "name": "Test User",
            "picture": {
                "data": {
                    "url": "https://example.com/photo.jpg"
                }
            }
        }

        async def mock_get(url, *args, **kwargs):
            if "oauth/access_token" in url:
                return HttpxResponse(200, json={
                    "access_token": "mock_fb_token",
                    "expires_in": 5184000
                })
            return HttpxResponse(200, json=mock_userinfo)

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = await FacebookOAuthService.get_facebook_user_info("test_code")

        assert result["id"] == "fb_123"
        assert result["email"] == "testuser@example.com"
        assert result["first_name"] == "Test"
        assert result["last_name"] == "User"
        assert result["access_token"] == "mock_fb_token"
        assert result["picture_url"] == "https://example.com/photo.jpg"
        assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_successful_token_exchange_no_picture(self):
        """Should handle missing picture gracefully"""
        mock_userinfo = {
            "id": "fb_no_pic",
            "email": "nopic@example.com",
            "first_name": "No",
            "last_name": "Pic",
            "name": "No Pic"
        }

        async def mock_get(url, *args, **kwargs):
            if "oauth/access_token" in url:
                return HttpxResponse(200, json={"access_token": "mock_token", "expires_in": 5184000})
            return HttpxResponse(200, json=mock_userinfo)

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            result = await FacebookOAuthService.get_facebook_user_info("test_code")

        assert result["id"] == "fb_no_pic"
        assert "picture_url" not in result or result.get("picture_url") is None

    @pytest.mark.asyncio
    async def test_token_exchange_failure(self):
        """Should raise HTTPException when token exchange fails"""
        async def mock_get_failure(url, *args, **kwargs):
            return HttpxResponse(400, json={"error": {"message": "Invalid code"}})

        with patch("httpx.AsyncClient.get", side_effect=mock_get_failure):
            with pytest.raises(HTTPException) as exc:
                await FacebookOAuthService.get_facebook_user_info("bad_code")
            assert exc.value.status_code == 400
            assert "Failed to authenticate" in exc.value.detail

    @pytest.mark.asyncio
    async def test_no_access_token_in_response(self):
        """Should raise HTTPException when no access_token returned"""
        async def mock_get_no_token(url, *args, **kwargs):
            return HttpxResponse(200, json={"error": "something_wrong"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get_no_token):
            with pytest.raises(HTTPException) as exc:
                await FacebookOAuthService.get_facebook_user_info("test_code")
            assert "No access token" in exc.value.detail

    @pytest.mark.asyncio
    async def test_userinfo_failure(self):
        """Should raise HTTPException when userinfo request fails"""
        call_count = [0]

        async def mock_get(url, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return HttpxResponse(200, json={"access_token": "mock_token", "expires_in": 5184000})
            return HttpxResponse(500, json={"error": {"message": "internal"}})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            with pytest.raises(HTTPException) as exc:
                await FacebookOAuthService.get_facebook_user_info("test_code")
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_token_exchange_uses_get(self):
        """Facebook token exchange should use GET (not POST)"""
        captured_methods = []

        async def mock_get(url, *args, **kwargs):
            return HttpxResponse(200, json={"access_token": "mock_token", "expires_in": 5184000})

        with patch("httpx.AsyncClient.get", side_effect=mock_get) as mock_get_method:
            with patch("httpx.AsyncClient.post") as mock_post:
                await FacebookOAuthService.get_facebook_user_info("test_code")
                mock_get_method.assert_called()
                mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_redirect_uri(self, db):
        """Should pass custom redirect URI to Facebook"""  # noqa: F811
        custom_uri = "http://custom/callback"
        captured_params = {}

        async def mock_get(url, *args, **kwargs):
            nonlocal captured_params
            captured_params = kwargs.get("params", {})
            if "oauth/access_token" in url:
                return HttpxResponse(200, json={"access_token": "mock_token", "expires_in": 5184000})
            return HttpxResponse(200, json={"id": "test", "email": "test@test.com"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            await FacebookOAuthService.get_facebook_user_info("code", custom_uri)

        assert captured_params.get("redirect_uri") == custom_uri

    @pytest.mark.asyncio
    async def test_userinfo_requests_correct_fields(self):
        """Should request specific fields from Facebook Graph API"""
        captured_params = {}

        async def mock_get(url, *args, **kwargs):
            nonlocal captured_params
            captured_params = kwargs.get("params", {})
            if "oauth/access_token" in url:
                return HttpxResponse(200, json={"access_token": "mock_token", "expires_in": 5184000})
            return HttpxResponse(200, json={"id": "test"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            await FacebookOAuthService.get_facebook_user_info("code")

        # Second call should have fields param
        assert "fields" in str(captured_params.get("fields", ""))
        assert "id" in captured_params.get("fields", "")
        assert "email" in captured_params.get("fields", "")
        assert "picture" in captured_params.get("fields", "")


# =============================================================
# Integration Tests: authenticate_or_create_user
# =============================================================

@pytest.mark.unit
class TestAuthenticateOrCreateUser:

    @pytest.mark.asyncio
    async def test_creates_new_user(self, db):
        """Should create a new user from Facebook info when none exists"""
        mock_data = {
            "id": "fb_456",
            "email": "newfbuser@example.com",
            "first_name": "New",
            "last_name": "FBUser",
            "name": "New FBUser",
            "picture_url": "https://example.com/pic.jpg",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.email == "newfbuser@example.com"
        assert user.oauth_provider == "facebook"
        assert user.oauth_id == "fb_456"
        assert user.is_verified is True
        assert user.role == UserRole.USER
        assert user.first_name == "New"
        assert user.last_name == "FBUser"

    @pytest.mark.asyncio
    async def test_finds_existing_oauth_user(self, db, test_user):
        """Should return existing user found by OAuth provider + id"""
        test_user.oauth_provider = "facebook"
        test_user.oauth_id = "existing_fb_id"
        db.commit()

        mock_data = {
            "id": "existing_fb_id",
            "email": test_user.email,
            "first_name": "Test",
            "last_name": "User",
            "name": "Test User",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_links_to_existing_email_user(self, db, test_user):
        """Should link Facebook OAuth to existing user found by email"""
        mock_data = {
            "id": "link_fb_id",
            "email": test_user.email,
            "first_name": "Updated",
            "last_name": "Name",
            "name": "Updated Name",
            "picture_url": "https://example.com/pic.jpg",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.id == test_user.id
        assert user.oauth_provider == "facebook"
        assert user.oauth_id == "link_fb_id"
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_updates_existing_user_profile(self, db, test_user):
        """Should update name and picture for existing OAuth user"""
        test_user.oauth_provider = "facebook"
        test_user.oauth_id = "update_fb_id"
        test_user.first_name = "Old"
        test_user.last_name = "Name"
        test_user.profile_picture = "https://old.example.com/pic.jpg"
        db.commit()

        mock_data = {
            "id": "update_fb_id",
            "email": test_user.email,
            "first_name": "New",
            "last_name": "Updated",
            "name": "New Updated",
            "picture_url": "https://new.example.com/pic.jpg",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.first_name == "New"
        assert user.last_name == "Updated"
        assert user.profile_picture == "https://new.example.com/pic.jpg"

    @pytest.mark.asyncio
    async def test_raises_on_missing_id(self, db):
        """Should raise when Facebook returns no id"""
        mock_data = {
            "email": "noid@example.com",
            "first_name": "No",
            "last_name": "Id",
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            with pytest.raises(HTTPException) as exc:
                await FacebookOAuthService.authenticate_or_create_user(db, "test_code")
            assert exc.value.status_code == 400
            assert "Insufficient user info" in exc.value.detail

    @pytest.mark.asyncio
    async def test_creates_user_without_email(self, db):
        """Should create user with fb_user_ fallback when no email"""
        mock_data = {
            "id": "no_email_fb_12345",
            "first_name": "NoEmail",
            "last_name": "User",
            "name": "NoEmail User",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.oauth_id == "no_email_fb_12345"
        assert user.email.endswith("@facebook.user")
        assert user.username.startswith("fb_user")

    @pytest.mark.asyncio
    async def test_uses_name_when_no_first_last_name(self, db):
        """Should split the full name when first/last name not provided"""
        mock_data = {
            "id": "name_split_id",
            "email": "namesplit@example.com",
            "name": "John Smith",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.first_name == "John"
        assert user.last_name == "Smith"

    @pytest.mark.asyncio
    async def test_uses_username_when_no_name_at_all(self, db):
        """Should fall back to username when neither name nor first/last name provided"""
        mock_data = {
            "id": "no_name_fb",
            "email": "noname@example.com",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.first_name is not None
        assert user.last_name is not None

    @pytest.mark.asyncio
    async def test_generates_unique_username(self, db, test_user):
        """Should generate unique username when base name exists"""
        mock_data = {
            "id": "unique_fb_id",
            "email": "testuser@example.com",
            "first_name": "Test",
            "last_name": "User",
            "name": "Test User",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.username.startswith("testuser")
        assert user.username != "testuser"

    @pytest.mark.asyncio
    async def test_new_user_has_random_password(self, db):
        """New OAuth user should have a hashed password (not plaintext)"""
        mock_data = {
            "id": "check_pw_fb",
            "email": "checkpwfb@example.com",
            "first_name": "Check",
            "last_name": "Pw",
            "name": "Check Pw",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.password_hash is not None
        assert user.password_hash != ""
        assert user.password_hash != user.email

    @pytest.mark.asyncio
    async def test_does_not_update_email_if_taken(self, db, test_user, test_admin):
        """Should not update email to one already used by another user"""
        test_user.oauth_provider = "facebook"
        test_user.oauth_id = "email_conflict_fb"
        test_user.email = "original@example.com"
        db.commit()

        mock_data = {
            "id": "email_conflict_fb",
            "email": test_admin.email,
            "first_name": "Test",
            "last_name": "User",
            "name": "Test User",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is False
        assert user.email == "original@example.com"

    @pytest.mark.asyncio
    async def test_links_and_splits_full_name(self, db):
        """When linking and no first/last name, should split full name"""
        mock_data = {
            "id": "link_split_name",
            "email": "linksplit@example.com",
            "name": "Jane Doe",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert is_new is True
        assert user.first_name == "Jane"
        assert user.last_name == "Doe"

    @pytest.mark.asyncio
    async def test_token_info_returned(self, db):
        """Should return token info dict with access_token and expiry"""
        mock_data = {
            "id": "token_info_fb",
            "email": "tokeninfofb@example.com",
            "first_name": "Token",
            "last_name": "Info",
            "name": "Token Info",
            "picture_url": None,
            "access_token": "returned_fb_token",
            "expires_in": 3600
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            user, is_new, token_info = await FacebookOAuthService.authenticate_or_create_user(db, "test_code")

        assert token_info["access_token"] == "returned_fb_token"
        assert token_info["expires_in"] == 3600
        assert "expires_at" in token_info


# =============================================================
# API Integration Tests (via test client)
# =============================================================

@pytest.mark.integration
class TestFacebookOAuthAPIEndpoints:

    def test_facebook_login_redirects(self, client, auth_url):
        """GET /api/v1/auth/facebook/login should redirect to Facebook"""
        response = client.get(f"{auth_url}/facebook/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers.get("location", "")
        assert "facebook.com" in location

    def test_facebook_callback_missing_code(self, client, auth_url):
        """GET /api/v1/auth/facebook/callback without code should return 422"""
        response = client.get(f"{auth_url}/facebook/callback", follow_redirects=False)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_facebook_callback_with_mocked_auth(self, client, auth_url, db):
        """GET /api/v1/auth/facebook/callback with mocked OAuth should redirect to frontend"""
        from app.dependencies.db import get_db

        mock_data = {
            "id": "callback_fb_id",
            "email": "fbcallback@example.com",
            "first_name": "Callback",
            "last_name": "User",
            "name": "Callback User",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.get(
                f"{auth_url}/facebook/callback?code=mocked_code",
                follow_redirects=False
            )
            app.dependency_overrides.clear()

        assert response.status_code in (302, 307)
        location = response.headers.get("location", "")
        assert settings.FRONTEND_URL in location
        assert "access_token" in location

    @pytest.mark.asyncio
    async def test_facebook_token_exchange_new_user(self, client, auth_url, db):
        """POST /api/v1/auth/facebook/token should return JWT tokens for new user"""
        from app.dependencies.db import get_db

        mock_data = {
            "id": "token_exchange_fb",
            "email": "fbtoken@example.com",
            "first_name": "Token",
            "last_name": "Exchange",
            "name": "Token Exchange",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/facebook/token",
                json={"code": "mocked_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["is_new_user"] is True
        assert data["data"]["email"] == "fbtoken@example.com"

    @pytest.mark.asyncio
    async def test_facebook_token_exchange_existing_user(self, client, auth_url, db, test_user):
        """POST /api/v1/auth/facebook/token should return JWT for existing user linking"""
        from app.dependencies.db import get_db

        mock_data = {
            "id": "link_existing_fb",
            "email": test_user.email,
            "first_name": test_user.first_name,
            "last_name": test_user.last_name,
            "name": f"{test_user.first_name} {test_user.last_name}",
            "picture_url": None,
            "access_token": "mock_at",
            "expires_in": 5184000
        }

        with patch.object(FacebookOAuthService, "get_facebook_user_info", AsyncMock(return_value=mock_data)):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/facebook/token",
                json={"code": "mocked_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_new_user"] is False
        assert data["data"]["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_facebook_token_exchange_failure(self, client, auth_url, db):
        """POST /api/v1/auth/facebook/token should return 400 on OAuth failure"""
        from app.dependencies.db import get_db

        with patch.object(
            FacebookOAuthService, "get_facebook_user_info",
            AsyncMock(side_effect=HTTPException(status_code=400, detail="Facebook authentication failed"))
        ):
            app = client.app
            app.dependency_overrides[get_db] = lambda: db
            response = client.post(
                f"{auth_url}/facebook/token",
                json={"code": "bad_code"}
            )
            app.dependency_overrides.clear()

        assert response.status_code == 400

    def test_facebook_token_exchange_no_code(self, client, auth_url):
        """POST /api/v1/auth/facebook/token without code should return 422"""
        response = client.post(f"{auth_url}/facebook/token", json={})
        assert response.status_code == 422
