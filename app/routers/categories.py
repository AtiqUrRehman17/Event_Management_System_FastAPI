from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_admin, get_current_user_optional
from app.models.user import User
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, 
    CategoryListResponse, PopularCategoryResponse, CategoryStatsResponse,
    CategoryTreeNode, CategoryTreeResponse
)
from app.services.category_service import CategoryService
from app.utils.response import success_response

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a new category with optional parent (Admin only)"""
    category = CategoryService.create_category(db, category_data)
    
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "icon": category.icon,
            "color": category.color,
            "image_url": category.image_url,
            "parent_id": category.parent_id,
            "level": category.level,
            "created_at": category.created_at,
            "updated_at": category.updated_at
        },
        message="Category created successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.get("/", response_model=dict)
async def get_all_categories(
    active_only: bool = Query(True, description="Show only active categories"),
    include_images: bool = Query(True, description="Include category images"),
    flat: bool = Query(False, description="Return as flat list instead of tree"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get all categories - can be flat or hierarchical tree"""
    if flat:
        categories = CategoryService.get_all_categories(db, active_only)
        data = [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "is_active": cat.is_active,
                "icon": cat.icon,
                "color": cat.color,
                "image_url": cat.image_url if include_images else None,
                "parent_id": cat.parent_id,
                "level": cat.level,
                "created_at": cat.created_at,
                "updated_at": cat.updated_at
            }
            for cat in categories
        ]
    else:
        # Return hierarchical tree
        data = CategoryService.get_category_tree(db, active_only)
    
    return success_response(
        data=data,
        message="Categories retrieved successfully"
    )


@router.get("/tree", response_model=dict)
async def get_category_tree(
    active_only: bool = Query(True, description="Show only active categories"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get categories as a hierarchical tree structure.
    Useful for dropdowns and nested displays.
    """
    tree = CategoryService.get_category_tree(db, active_only)
    return success_response(
        data=tree,
        message="Category tree retrieved successfully"
    )


@router.get("/popular", response_model=dict)
async def get_popular_categories(
    limit: int = Query(6, ge=1, le=20, description="Number of categories to return"),
    sort_by: str = Query("events_count", regex="^(events_count|total_bookings|revenue|seats_booked)$", 
                         description="Sort by: events_count, total_bookings, revenue, or seats_booked"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get popular categories for dashboard display."""
    popular_categories = CategoryService.get_popular_categories(db, limit, sort_by)
    
    return success_response(
        data=popular_categories,
        message="Popular categories retrieved successfully"
    )


@router.get("/featured", response_model=dict)
async def get_featured_categories(
    limit: int = Query(4, ge=1, le=10, description="Number of featured categories to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get featured categories for homepage display."""
    categories = CategoryService.get_featured_categories(db, limit)
    
    return success_response(
        data=[
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "color": cat.color,
                "image_url": cat.image_url,
                "description": cat.description,
                "level": cat.level
            }
            for cat in categories
        ],
        message="Featured categories retrieved successfully"
    )


@router.get("/breadcrumb/{category_id}", response_model=dict)
async def get_category_breadcrumb(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get breadcrumb trail for a category (parent chain)"""
    breadcrumb = CategoryService.get_category_breadcrumb(db, category_id)
    return success_response(
        data=breadcrumb,
        message="Breadcrumb retrieved successfully"
    )


@router.get("/children/{parent_id}", response_model=dict)
async def get_child_categories(
    parent_id: int,
    active_only: bool = Query(True, description="Show only active categories"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get direct child categories of a parent"""
    children = CategoryService.get_child_categories(db, parent_id, active_only)
    
    return success_response(
        data=[
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "color": cat.color,
                "image_url": cat.image_url,
                "level": cat.level,
                "events_count": CategoryService.get_category_event_count(db, cat.id)
            }
            for cat in children
        ],
        message="Child categories retrieved successfully"
    )


@router.get("/ancestors/{category_id}", response_model=dict)
async def get_category_ancestors(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get all ancestors of a category (parent, grandparent, etc.)"""
    ancestors = CategoryService.get_ancestors(db, category_id)
    
    return success_response(
        data=[
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "color": cat.color,
                "level": cat.level
            }
            for cat in ancestors
        ],
        message="Ancestors retrieved successfully"
    )


@router.get("/descendants/{category_id}", response_model=dict)
async def get_category_descendants(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get all descendants of a category (children, grandchildren, etc.)"""
    descendants = CategoryService.get_descendants(db, category_id)
    
    return success_response(
        data=[
            {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "color": cat.color,
                "level": cat.level,
                "parent_id": cat.parent_id
            }
            for cat in descendants
        ],
        message="Descendants retrieved successfully"
    )


@router.get("/stats/{category_id}", response_model=dict)
async def get_category_stats(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get detailed statistics for a specific category including children."""
    stats = CategoryService.get_category_stats(db, category_id)
    
    return success_response(
        data=stats,
        message="Category statistics retrieved successfully"
    )


@router.get("/icon-map", response_model=dict)
async def get_category_icon_map(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get mapping of category IDs to icon/color/image info"""
    icon_map = CategoryService.get_categories_with_icon_map(db)
    return success_response(
        data=icon_map,
        message="Category icon map retrieved successfully"
    )


@router.get("/{category_id}", response_model=dict)
async def get_category(
    category_id: int,
    include_children: bool = Query(False, description="Include child categories"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get category by ID with optional child categories"""
    category = CategoryService.get_category_by_id(db, category_id)
    
    data = {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "is_active": category.is_active,
        "icon": category.icon,
        "color": category.color,
        "image_url": category.image_url,
        "parent_id": category.parent_id,
        "level": category.level,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
        "events_count": CategoryService.get_category_event_count(db, category_id)
    }
    
    if include_children:
        children = CategoryService.get_child_categories(db, category_id, active_only=True)
        data["children"] = [
            {
                "id": child.id,
                "name": child.name,
                "icon": child.icon,
                "color": child.color,
                "events_count": CategoryService.get_category_event_count(db, child.id)
            }
            for child in children
        ]
    
    return success_response(
        data=data,
        message="Category retrieved successfully"
    )


@router.put("/{category_id}", response_model=dict)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Update category including parent relationship (Admin only)"""
    category = CategoryService.update_category(db, category_id, category_data)
    
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "is_active": category.is_active,
            "icon": category.icon,
            "color": category.color,
            "image_url": category.image_url,
            "parent_id": category.parent_id,
            "level": category.level,
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
    """Delete category - children will be moved to parent (Admin only)"""
    CategoryService.delete_category(db, category_id)
    
    return success_response(
        data=None,
        message="Category deleted successfully"
    )