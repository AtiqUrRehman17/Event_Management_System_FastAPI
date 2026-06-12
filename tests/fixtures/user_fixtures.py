# tests/fixtures/user_fixtures.py


def get_valid_user_data():
    """Valid user registration data"""
    return {
        "username": "fixtureuser",
        "email": "fixtureuser@example.com",
        "password": "FixturePass@123",
        "first_name": "Fixture",
        "last_name": "User"
    }


def get_valid_admin_data():
    """Valid admin user data"""
    return {
        "username": "fixtureadmin",
        "email": "fixtureadmin@example.com",
        "password": "FixtureAdmin@123",
        "first_name": "Fixture",
        "last_name": "Admin"
    }


def get_invalid_user_data_missing_email():
    """User data with missing email"""
    return {
        "username": "fixtureuser",
        "password": "FixturePass@123",
        "first_name": "Fixture",
        "last_name": "User"
    }


def get_invalid_user_data_weak_password():
    """User data with weak password"""
    return {
        "username": "fixtureuser",
        "email": "fixtureuser@example.com",
        "password": "weak",
        "first_name": "Fixture",
        "last_name": "User"
    }


def get_invalid_user_data_bad_email():
    """User data with invalid email format"""
    return {
        "username": "fixtureuser",
        "email": "not-an-email",
        "password": "FixturePass@123",
        "first_name": "Fixture",
        "last_name": "User"
    }


def get_invalid_user_data_short_username():
    """User data with too short username"""
    return {
        "username": "ab",
        "email": "fixtureuser@example.com",
        "password": "FixturePass@123",
        "first_name": "Fixture",
        "last_name": "User"
    }


def get_user_profile_update_data():
    """Valid profile update data"""
    return {
        "first_name": "Updated",
        "last_name": "Name",
        "bio": "This is an updated bio",
        "phone": "+1234567890",
        "timezone": "America/New_York"
    }


def get_change_password_data():
    """Valid change password data"""
    return {
        "current_password": "TestPass@123",
        "new_password": "NewPass@456",
        "confirm_password": "NewPass@456"
    }


def get_change_password_wrong_current():
    """Change password with wrong current password"""
    return {
        "current_password": "WrongPass@123",
        "new_password": "NewPass@456",
        "confirm_password": "NewPass@456"
    }


def get_change_password_mismatch():
    """Change password with mismatched new passwords"""
    return {
        "current_password": "TestPass@123",
        "new_password": "NewPass@456",
        "confirm_password": "DifferentPass@456"
    }


def get_multiple_users_data():
    """List of multiple valid users data"""
    return [
        {
            "username": "user_one",
            "email": "userone@example.com",
            "password": "UserOne@123",
            "first_name": "User",
            "last_name": "One"
        },
        {
            "username": "user_two",
            "email": "usertwo@example.com",
            "password": "UserTwo@123",
            "first_name": "User",
            "last_name": "Two"
        },
        {
            "username": "user_three",
            "email": "userthree@example.com",
            "password": "UserThree@123",
            "first_name": "User",
            "last_name": "Three"
        }
    ]


def get_login_data():
    """Valid login credentials"""
    return {
        "username": "testuser",
        "password": "TestPass@123"
    }


def get_login_data_wrong_password():
    """Login with wrong password"""
    return {
        "username": "testuser",
        "password": "WrongPass@123"
    }


def get_login_data_wrong_username():
    """Login with non-existent username"""
    return {
        "username": "nonexistentuser",
        "password": "TestPass@123"
    }


def get_forgot_password_data():
    """Forgot password request data"""
    return {
        "email": "testuser@example.com"
    }


def get_reset_password_data(token: str):
    """Reset password request data"""
    return {
        "token": token,
        "new_password": "NewPass@456",
        "confirm_password": "NewPass@456"
    }