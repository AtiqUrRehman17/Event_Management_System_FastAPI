import pytest
from app.utils.auth_utils import hash_password, verify_password


@pytest.mark.unit
class TestHashPassword:

    def test_hash_password_returns_string(self):
        """Hash should return a string"""
        result = hash_password("TestPass@123")
        assert isinstance(result, str)

    def test_hash_password_not_equal_to_plain(self):
        """Hash should not equal the plain password"""
        plain = "TestPass@123"
        result = hash_password(plain)
        assert result != plain

    def test_hash_password_different_each_time(self):
        """Same password should produce different hashes (due to salt)"""
        hash1 = hash_password("TestPass@123")
        hash2 = hash_password("TestPass@123")
        assert hash1 != hash2

    def test_hash_password_not_empty(self):
        """Hash should not be empty"""
        result = hash_password("TestPass@123")
        assert len(result) > 0


@pytest.mark.unit
class TestVerifyPassword:

    def test_verify_correct_password(self):
        """Correct password should verify successfully"""
        plain = "TestPass@123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password should fail verification"""
        hashed = hash_password("TestPass@123")
        assert verify_password("WrongPass@123", hashed) is False

    def test_verify_empty_password(self):
        """Empty password should fail verification"""
        hashed = hash_password("TestPass@123")
        assert verify_password("", hashed) is False

    def test_verify_invalid_hash(self):
        """Invalid hash should return False not raise exception"""
        result = verify_password("TestPass@123", "not-a-valid-hash")
        assert result is False

    def test_verify_case_sensitive(self):
        """Password verification should be case sensitive"""
        hashed = hash_password("TestPass@123")
        assert verify_password("testpass@123", hashed) is False