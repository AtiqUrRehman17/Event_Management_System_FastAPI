import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Define upload directories
BASE_UPLOAD_DIR = Path(settings.UPLOAD_DIR)
EVENT_IMAGES_DIR = BASE_UPLOAD_DIR / "events"
CATEGORY_IMAGES_DIR = BASE_UPLOAD_DIR / "categories"
USER_AVATARS_DIR = BASE_UPLOAD_DIR / "avatars"

# Allowed extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Max file size (5MB default)
MAX_FILE_SIZE = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024


def ensure_upload_dirs():
    """Create upload directories if they don't exist"""
    for dir_path in [EVENT_IMAGES_DIR, CATEGORY_IMAGES_DIR, USER_AVATARS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)


def validate_image(file: UploadFile) -> tuple:
    """
    Validate uploaded image file.
    Returns (is_valid, error_message)
    """
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Max size: {settings.MAX_IMAGE_SIZE_MB}MB"
    
    return True, None


def upload_event_image(file: UploadFile, event_id: int) -> str:
    """
    Upload image for an event.
    Returns the file path relative to static directory.
    """
    ensure_upload_dirs()
    
    # Validate image
    is_valid, error = validate_image(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"event_{event_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    # Save file
    file_path = EVENT_IMAGES_DIR / unique_filename
    relative_path = f"/uploads/events/{unique_filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Optional: Optimize image
        optimize_image(file_path)
        
        logger.info(f"Image uploaded: {relative_path} for event {event_id}")
        return relative_path
        
    except Exception as e:
        logger.error(f"Failed to upload image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image file"
        )


def upload_category_image(file: UploadFile, category_id: int) -> str:
    """
    Upload image for a category.
    Returns the file path relative to static directory.
    """
    ensure_upload_dirs()
    
    is_valid, error = validate_image(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"category_{category_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    file_path = CATEGORY_IMAGES_DIR / unique_filename
    relative_path = f"/uploads/categories/{unique_filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        optimize_image(file_path)
        return relative_path
        
    except Exception as e:
        logger.error(f"Failed to upload category image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image file"
        )


def upload_user_avatar(file: UploadFile, user_id: int) -> str:
    """
    Upload avatar for a user.
    Returns the file path relative to static directory.
    """
    ensure_upload_dirs()
    
    is_valid, error = validate_image(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"user_{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    
    file_path = USER_AVATARS_DIR / unique_filename
    relative_path = f"/uploads/avatars/{unique_filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create thumbnail for avatar
        create_thumbnail(file_path, USER_AVATARS_DIR / f"thumb_{unique_filename}")
        
        return relative_path
        
    except Exception as e:
        logger.error(f"Failed to upload avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image file"
        )


def optimize_image(file_path: Path, max_width: int = 1200, quality: int = 85):
    """
    Optimize image: resize if too large, compress, convert to RGB.
    """
    try:
        with Image.open(file_path) as img:
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Resize if too large
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save with compression
            img.save(file_path, 'JPEG', quality=quality, optimize=True)
            
    except Exception as e:
        logger.warning(f"Image optimization failed: {str(e)}")


def create_thumbnail(file_path: Path, thumb_path: Path, size: tuple = (150, 150)):
    """
    Create a thumbnail image.
    """
    try:
        with Image.open(file_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=75, optimize=True)
    except Exception as e:
        logger.warning(f"Thumbnail creation failed: {str(e)}")


def delete_image(file_path: str) -> bool:
    """
    Delete an image file.
    """
    if not file_path or not file_path.startswith("/uploads/"):
        return False
    
    # Convert URL path to filesystem path
    relative_path = file_path.replace("/uploads/", "")
    
    # Check all possible directories
    for base_dir in [EVENT_IMAGES_DIR, CATEGORY_IMAGES_DIR, USER_AVATARS_DIR]:
        full_path = base_dir / Path(relative_path).name
        if full_path.exists():
            try:
                full_path.unlink()
                # Also delete thumbnail if exists
                thumb_path = base_dir / f"thumb_{full_path.name}"
                if thumb_path.exists():
                    thumb_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Failed to delete image: {str(e)}")
                return False
    
    return False