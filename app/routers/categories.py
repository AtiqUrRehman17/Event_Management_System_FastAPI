from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.dependencies import get_db, get_current_admin, get_current_user_optional
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services.category_service import CategoryService
from app.utils.response import success_response

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Create a new category (Admin only)
    """
    category = CategoryService.create_category(db, category_data)
    
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        },
        message="Category created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/", response_model=dict)
async def get_all_categories(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get all categories (Public access)
    """
    categories = CategoryService.get_all_categories(db, active_only)
    
    return success_response(
        data=[
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "is_active": cat.is_active,
                "created_at": cat.created_at,
                "updated_at": cat.updated_at
            }
            for cat in categories
        ],
        message="Categories retrieved successfully"
    )


@router.get("/{category_id}", response_model=dict)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get category by ID (Public access)
    """
    category = CategoryService.get_category_by_id(db, category_id)
    
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        },
        message="Category retrieved successfully"
    )


@router.put("/{category_id}", response_model=dict)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Update category (Admin only)
    """
    category = CategoryService.update_category(db, category_id, category_data)
    
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        },
        message="Category updated successfully"
    )


@router.delete("/{category_id}", response_model=dict)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Delete category (Admin only)
    """
    CategoryService.delete_category(db, category_id)
    
    return success_response(
        data=None,
        message="Category deleted successfully"
    )