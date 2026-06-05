import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format
    """
    if not email:
        return False, "Email is required"
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False, "Invalid email format"
    
    return True, ""


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, ""


def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, str]:
    """
    Validate name fields
    """
    if not name or not name.strip():
        return False, f"{field_name} is required"
    
    if len(name.strip()) < 2:
        return False, f"{field_name} must be at least 2 characters long"
    
    if len(name.strip()) > 100:
        return False, f"{field_name} must be less than 100 characters"
    
    return True, ""