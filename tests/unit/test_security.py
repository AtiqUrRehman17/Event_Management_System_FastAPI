import pytest
from datetime import timedelta
from app.core.security import Security
from app.core.exceptions import TokenExpiredException, InvalidTokenException


@pytest.mark.unit
class TestCreateAccessToken:

    def test_creates_token(self):
        """Should create a non-empty token string"""
        token = Security.create_access_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_parts(self):
        """JWT token should have 3 parts separated by dots"""
        token = Security.create_access_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_without_user_info(self):
        """Should create token even without user_info"""
        token = Security.create_access_token(data={"sub": "1"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_with_custom_expiry(self):
        """Should create token with custom expiry"""
        token = Security.create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(hours=2)
        )
        assert isinstance(token, str)


@pytest.mark.unit
class TestCreateRefreshToken:

    def test_creates_refresh_token(self):
        """Should create a non-empty refresh token"""
        token = Security.create_refresh_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_refresh_token_different_from_access(self):
        """Refresh token should be different from access token"""
        data = {"sub": "1"}
        user_info = {"username": "test", "email": "test@test.com", "role": "user"}
        access = Security.create_access_token(data=data, user_info=user_info)
        refresh = Security.create_refresh_token(data=data, user_info=user_info)
        assert access != refresh


@pytest.mark.unit
class TestVerifyToken:

    def test_verify_valid_access_token(self):
        """Should verify a valid access token"""
        token = Security.create_access_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        payload = Security.verify_token(token, token_type="access")
        assert payload is not None
        assert payload.get("sub") == "1"

    def test_verify_valid_refresh_token(self):
        """Should verify a valid refresh token"""
        token = Security.create_refresh_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        payload = Security.verify_token(token, token_type="refresh")
        assert payload is not None
        assert payload.get("sub") == "1"

    def test_verify_wrong_token_type(self):
        """Should raise error when token type doesn't match"""
        access_token = Security.create_access_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        with pytest.raises(InvalidTokenException):
            Security.verify_token(access_token, token_type="refresh")

    def test_verify_expired_token(self):
        """Should raise TokenExpiredException for expired token"""
        token = Security.create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        with pytest.raises(TokenExpiredException):
            Security.verify_token(token, token_type="access")

    def test_verify_invalid_token(self):
        """Should raise InvalidTokenException for garbage token"""
        with pytest.raises(InvalidTokenException):
            Security.verify_token("this.is.not.valid", token_type="access")

    def test_verify_empty_token(self):
        """Should raise InvalidTokenException for empty token"""
        with pytest.raises(InvalidTokenException):
            Security.verify_token("", token_type="access")

    def test_payload_contains_correct_claims(self):
        """Token payload should contain expected claims"""
        token = Security.create_access_token(
            data={"sub": "42"},
            user_info={"username": "john", "email": "john@test.com", "role": "user"}
        )
        payload = Security.verify_token(token, token_type="access")
        assert payload.get("sub") == "42"
        assert payload.get("username") == "john"
        assert payload.get("email") == "john@test.com"
        assert payload.get("role") == "user"
        assert payload.get("type") == "access"
        assert payload.get("jti") is not None


@pytest.mark.unit
class TestGetTokenClaims:

    def test_get_claims_from_valid_token(self):
        """Should get claims from valid token"""
        token = Security.create_access_token(
            data={"sub": "1"},
            user_info={"username": "test", "email": "test@test.com", "role": "user"}
        )
        claims = Security.get_token_claims(token)
        assert claims.get("sub") == "1"

    def test_get_claims_from_expired_token(self):
        """Should get claims from expired token without raising"""
        token = Security.create_access_token(
            data={"sub": "99"},
            expires_delta=timedelta(seconds=-1)
        )
        claims = Security.get_token_claims(token)
        assert claims.get("sub") == "99"

    def test_get_claims_invalid_token(self):
        """Should raise InvalidTokenException for garbage"""
        with pytest.raises(InvalidTokenException):
            Security.get_token_claims("garbage.token.here")