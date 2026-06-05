from sqlalchemy.orm import Session
from typing import List, Tuple, Optional
from datetime import datetime
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.core.exceptions import CategoryNotFoundException, CategoryAlreadyExistsException


class CategoryService:
    
    @staticmethod
    def create_category(db: Session, category_data: CategoryCreate) -> Category:
        """Create a new category"""
        # Check if category already exists
        existing = db.query(Category).filter(Category.name == category_data.name).first()
        if existing:
            raise CategoryAlreadyExistsException()
        
        category = Category(
            name=category_data.name,
            description=category_data.description
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        return category
    
    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Category:
        """Get category by ID"""
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise CategoryNotFoundException()
        return category
    
    @staticmethod
    def get_all_categories(db: Session, active_only: bool = True) -> List[Category]:
        """Get all categories"""
        query = db.query(Category)
        if active_only:
            query = query.filter(Category.is_active == True)
        return query.order_by(Category.name).all()
    
    @staticmethod
    def update_category(db: Session, category_id: int, category_data: CategoryUpdate) -> Category:
        """Update category"""
        category = CategoryService.get_category_by_id(db, category_id)
        
        if category_data.name and category_data.name != category.name:
            # Check if new name is already taken
            existing = db.query(Category).filter(Category.name == category_data.name).first()
            if existing:
                raise CategoryAlreadyExistsException()
            category.name = category_data.name
        
        if category_data.description is not None:
            category.description = category_data.description
        
        if category_data.is_active is not None:
            category.is_active = category_data.is_active
        
        category.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(category)
        
        return category
    
    @staticmethod
    def delete_category(db: Session, category_id: int) -> None:
        """Delete category (will set category_id to null in events)"""
        category = CategoryService.get_category_by_id(db, category_id)
        db.delete(category)
        db.commit()