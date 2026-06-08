from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_user, get_current_admin
from app.models.user import User
from app.schemas.user import UserProfileUpdate, ChangePasswordRequest
from app.services.user_service import UserService
from app.utils.response import success_response, paginated_response
from app.core.enums import UserRole
from app.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=dict)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's complete profile"""
    return success_response(
        data={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "phone": current_user.phone,
            "bio": current_user.bio,
            "timezone": current_user.timezone,
            "profile_picture": current_user.profile_picture,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        },
        message="User profile retrieved successfully"
    )


@router.put("/me", response_model=dict)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    Can update: first_name, last_name, email, phone, bio, timezone, profile_picture
    """
    updated_user = UserService.update_user_profile(db, current_user.id, profile_data)

    return success_response(
        data={
            "id": updated_user.id,
            "username": updated_user.username,
            "email": updated_user.email,
            "first_name": updated_user.first_name,
            "last_name": updated_user.last_name,
            "full_name": updated_user.full_name,
            "role": updated_user.role,
            "is_active": updated_user.is_active,
            "is_verified": updated_user.is_verified,
            "phone": updated_user.phone,
            "bio": updated_user.bio,
            "timezone": updated_user.timezone,
            "profile_picture": updated_user.profile_picture,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at
        },
        message="Profile updated successfully"
    )


@router.post("/me/change-password", response_model=dict)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    Requires current password for verification.
    """
    # Validate new password matches confirmation
    if password_data.new_password != password_data.confirm_password:
        return {
            "success": False,
            "message": "New password and confirmation do not match",
            "error_code": "PASSWORD_MISMATCH"
        }
    
    updated_user = UserService.change_password(
        db=db,
        user_id=current_user.id,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )

    return success_response(
        data={
            "message": "Password changed successfully. Please login again with your new password."
        },
        message="Password changed successfully"
    )


@router.get("/", response_model=dict)
async def get_all_users(
    pagination: PaginationParams = Depends(get_pagination_params),
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Get all users with pagination (Admin only)"""
    users, total = UserService.get_all_users(db, pagination, role, search)

    user_responses = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "phone": user.phone,
            "bio": user.bio,
            "timezone": user.timezone,
            "profile_picture": user.profile_picture,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        for user in users
    ]

    return paginated_response(
        items=user_responses,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
        message="Users retrieved successfully"
    )


@router.get("/{user_id}", response_model=dict)
async def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Get user by ID (Admin only)"""
    user = UserService.get_user_by_id(db, user_id)

    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "phone": user.phone,
            "bio": user.bio,
            "timezone": user.timezone,
            "profile_picture": user.profile_picture,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        },
        message="User retrieved successfully"
    )


@router.put("/{user_id}/deactivate", response_model=dict)
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Deactivate a user account (Admin only)"""
    user = UserService.deactivate_user(db, user_id)

    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active
        },
        message="User deactivated successfully"
    )


@router.put("/{user_id}/activate", response_model=dict)
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Activate a user account (Admin only)"""
    user = UserService.activate_user(db, user_id)

    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active
        },
        message="User activated successfully"
    )