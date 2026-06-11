from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.dependencies import get_db, get_current_admin, get_current_user
from app.models.user import User
from app.models.event import Event
from app.services.event_service import EventService
from app.utils.image_upload import upload_event_image, upload_category_image, upload_user_avatar, delete_image
from app.utils.response import success_response
from app.core.exceptions import EventNotFoundException

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/event/{event_id}", response_model=dict)
async def upload_event_image_endpoint(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Upload an image for an event (Admin only).
    Supported formats: JPG, PNG, GIF, WEBP
    Max size: 5MB
    """
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise EventNotFoundException()
    
    # Upload image
    image_path = upload_event_image(file, event_id)
    
    # Update event with new image URL
    event.image_url = image_path
    db.commit()
    
    return success_response(
        data={
            "event_id": event_id,
            "image_url": image_path,
            "message": "Image uploaded successfully"
        },
        message="Event image uploaded"
    )


@router.post("/category/{category_id}", response_model=dict)
async def upload_category_image_endpoint(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Upload an image for a category (Admin only).
    """
    from app.services.category_service import CategoryService
    from app.models.category import Category
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    image_path = upload_category_image(file, category_id)
    
    # Update category with new image URL
    category.image_url = image_path
    db.commit()
    
    return success_response(
        data={
            "category_id": category_id,
            "image_url": image_path,
            "message": "Image uploaded successfully"
        },
        message="Category image uploaded"
    )


@router.post("/avatar", response_model=dict)
async def upload_user_avatar_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload avatar for current user.
    """
    # Delete old avatar if exists
    if current_user.profile_picture and current_user.profile_picture.startswith("/uploads/"):
        delete_image(current_user.profile_picture)
    
    image_path = upload_user_avatar(file, current_user.id)
    
    # Update user with new avatar URL
    current_user.profile_picture = image_path
    db.commit()
    
    return success_response(
        data={
            "avatar_url": image_path,
            "message": "Avatar uploaded successfully"
        },
        message="Avatar uploaded"
    )


@router.delete("/event/{event_id}", response_model=dict)
async def delete_event_image(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Delete event image (Admin only).
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise EventNotFoundException()
    
    if event.image_url and delete_image(event.image_url):
        event.image_url = None
        db.commit()
        return success_response(
            data={"message": "Image deleted successfully"},
            message="Image deleted"
        )
    else:
        return success_response(
            data={"message": "No image to delete"},
            message="No image found"
        )