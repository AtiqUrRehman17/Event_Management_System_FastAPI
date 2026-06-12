import pytest
from app.utils.validators import (
    validate_email,
    validate_password_strength,
    validate_name
)


@pytest.mark.unit
class TestValidateEmail:

    def test_valid_email(self):
        """Valid email should pass"""
        is_valid, error = validate_email("user@example.com")
        assert is_valid is True
        assert error == ""

    def test_valid_email_with_subdomain(self):
        """Valid email with subdomain should pass"""
        is_valid, error = validate_email("user@mail.example.com")
        assert is_valid is True

    def test_empty_email(self):
        """Empty email should fail"""
        is_valid, error = validate_email("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_missing_at_symbol(self):
        """Email without @ should fail"""
        is_valid, error = validate_email("userexample.com")
        assert is_valid is False

    def test_missing_domain(self):
        """Email without domain should fail"""
        is_valid, error = validate_email("user@")
        assert is_valid is False

    def test_missing_username(self):
        """Email without username should fail"""
        is_valid, error = validate_email("@example.com")
        assert is_valid is False

    def test_invalid_format(self):
        """Completely invalid email should fail"""
        is_valid, error = validate_email("not-an-email")
        assert is_valid is False


@pytest.mark.unit
class TestValidatePasswordStrength:

    def test_valid_strong_password(self):
        """Strong password should pass"""
        is_valid, error = validate_password_strength("TestPass@123")
        assert is_valid is True
        assert error == ""

    def test_empty_password(self):
        """Empty password should fail"""
        is_valid, error = validate_password_strength("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_too_short(self):
        """Password shorter than 8 chars should fail"""
        is_valid, error = validate_password_strength("Abc@1")
        assert is_valid is False
        assert "8" in error

    def test_no_uppercase(self):
        """Password without uppercase should fail"""
        is_valid, error = validate_password_strength("testpass@123")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_no_lowercase(self):
        """Password without lowercase should fail"""
        is_valid, error = validate_password_strength("TESTPASS@123")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_no_digit(self):
        """Password without digit should fail"""
        is_valid, error = validate_password_strength("TestPass@abc")
        assert is_valid is False
        assert "digit" in error.lower()

    def test_exactly_8_chars(self):
        """Password with exactly 8 chars should pass if meets all rules"""
        is_valid, error = validate_password_strength("Test@12a")
        assert is_valid is True


@pytest.mark.unit
class TestValidateName:

    def test_valid_name(self):
        """Valid name should pass"""
        is_valid, error = validate_name("John")
        assert is_valid is True
        assert error == ""

    def test_valid_name_with_spaces(self):
        """Name with spaces should pass"""
        is_valid, error = validate_name("John Doe")
        assert is_valid is True

    def test_empty_name(self):
        """Empty name should fail"""
        is_valid, error = validate_name("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_whitespace_only(self):
        """Whitespace only name should fail"""
        is_valid, error = validate_name("   ")
        assert is_valid is False

    def test_too_short(self):
        """Name shorter than 2 chars should fail"""
        is_valid, error = validate_name("A")
        assert is_valid is False
        assert "2" in error

    def test_too_long(self):
        """Name longer than 100 chars should fail"""
        is_valid, error = validate_name("A" * 101)
        assert is_valid is False

    def test_custom_field_name(self):
        """Custom field name should appear in error message"""
        is_valid, error = validate_name("", field_name="First Name")
        assert "First Name" in error

    def test_exactly_2_chars(self):
        """Name with exactly 2 chars should pass"""
        is_valid, error = validate_name("Jo")
        assert is_valid is True