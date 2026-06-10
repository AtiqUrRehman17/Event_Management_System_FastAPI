from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from app.models.category import Category
from app.models.event import Event
from app.models.booking import Booking
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryTreeNode, CategoryTreeResponse
from app.core.exceptions import CategoryNotFoundException, CategoryAlreadyExistsException
from app.core.enums import EventStatus, BookingStatus
from app.utils.datetime_utils import get_current_utc
import logging

logger = logging.getLogger(__name__)


class CategoryService:
    
    @staticmethod
    def _update_path_and_level(db: Session, category: Category) -> None:
        """Update the path and level for a category based on its parent"""
        if category.parent_id:
            parent = db.query(Category).filter(Category.id == category.parent_id).first()
            if parent:
                category.level = parent.level + 1
                category.path = f"{parent.path}/{category.id}" if parent.path else f"{parent.id}/{category.id}"
            else:
                category.level = 0
                category.path = str(category.id)
        else:
            category.level = 0
            category.path = str(category.id)
    
    @staticmethod
    def _validate_parent_assignment(db: Session, category_id: int, parent_id: int) -> None:
        """Validate that a category can be assigned to a parent"""
        if category_id == parent_id:
            raise ValueError("A category cannot be its own parent")
        
        # Check for circular reference
        parent = db.query(Category).filter(Category.id == parent_id).first()
        while parent:
            if parent.parent_id == category_id:
                raise ValueError("Cannot assign parent that creates a circular reference")
            parent = db.query(Category).filter(Category.id == parent.parent_id).first()
    
    @staticmethod
    def create_category(db: Session, category_data: CategoryCreate) -> Category:
        """Create a new category with optional parent"""
        # Check if category already exists
        existing = db.query(Category).filter(Category.name == category_data.name).first()
        if existing:
            raise CategoryAlreadyExistsException()
        
        # Validate parent if provided
        parent_id = category_data.parent_id
        if parent_id:
            parent = db.query(Category).filter(Category.id == parent_id).first()
            if not parent:
                raise ValueError(f"Parent category with id {parent_id} not found")
            CategoryService._validate_parent_assignment(db, 0, parent_id)
        
        category = Category(
            name=category_data.name,
            description=category_data.description,
            icon=category_data.icon or "fa-tag",
            color=category_data.color or "#3498db",
            image_url=category_data.image_url,
            parent_id=parent_id
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        # Update path and level after commit (since we need the ID)
        CategoryService._update_path_and_level(db, category)
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
        """Get all categories with icon, color, and image"""
        query = db.query(Category)
        if active_only:
            query = query.filter(Category.is_active == True)
        return query.order_by(Category.level, Category.name).all()
    
    @staticmethod
    def get_category_tree(db: Session, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get categories as a hierarchical tree structure"""
        # Get all categories
        query = db.query(Category)
        if active_only:
            query = query.filter(Category.is_active == True)
        categories = query.all()
        
        # Build mapping of id to category dict
        category_map = {}
        for cat in categories:
            category_map[cat.id] = {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon,
                "color": cat.color,
                "image_url": cat.image_url,
                "level": cat.level,
                "parent_id": cat.parent_id,
                "children": []
            }
        
        # Build tree
        roots = []
        for cat in categories:
            if cat.parent_id is None:
                roots.append(category_map[cat.id])
            else:
                if cat.parent_id in category_map:
                    category_map[cat.parent_id]["children"].append(category_map[cat.id])
        
        return roots
    
    @staticmethod
    def update_category(db: Session, category_id: int, category_data: CategoryUpdate) -> Category:
        """Update category including hierarchy"""
        category = CategoryService.get_category_by_id(db, category_id)
        
        if category_data.name and category_data.name != category.name:
            existing = db.query(Category).filter(Category.name == category_data.name).first()
            if existing:
                raise CategoryAlreadyExistsException()
            category.name = category_data.name
        
        if category_data.description is not None:
            category.description = category_data.description
        
        if category_data.is_active is not None:
            category.is_active = category_data.is_active
        
        if category_data.icon is not None:
            category.icon = category_data.icon
        
        if category_data.color is not None:
            category.color = category_data.color
        
        if category_data.image_url is not None:
            category.image_url = category_data.image_url
        
        # Update parent if changed
        if category_data.parent_id is not None and category_data.parent_id != category.parent_id:
            if category_data.parent_id == 0:
                # Move to root level
                category.parent_id = None
            else:
                # Validate new parent
                CategoryService._validate_parent_assignment(db, category_id, category_data.parent_id)
                parent = db.query(Category).filter(Category.id == category_data.parent_id).first()
                if not parent:
                    raise ValueError(f"Parent category with id {category_data.parent_id} not found")
                category.parent_id = category_data.parent_id
            
            # Update path and level
            CategoryService._update_path_and_level(db, category)
        
        category.updated_at = get_current_utc()
        db.commit()
        db.refresh(category)
        
        return category
    
    @staticmethod
    def delete_category(db: Session, category_id: int) -> None:
        """Delete category (will set category_id to null in events and children)"""
        category = CategoryService.get_category_by_id(db, category_id)
        
        # Move children to parent or make them root
        for child in category.children:
            child.parent_id = category.parent_id
            CategoryService._update_path_and_level(db, child)
        
        db.delete(category)
        db.commit()
    
    @staticmethod
    def get_categories_with_icon_map(db: Session) -> dict:
        """Get dictionary mapping category ID to icon/color/image info"""
        categories = CategoryService.get_all_categories(db, active_only=True)
        return {
            cat.id: {
                "name": cat.name,
                "icon": cat.icon,
                "color": cat.color,
                "image_url": cat.image_url,
                "parent_id": cat.parent_id,
                "level": cat.level
            }
            for cat in categories
        }
    
    @staticmethod
    def get_category_breadcrumb(db: Session, category_id: int) -> List[Dict[str, Any]]:
        """Get breadcrumb trail for a category"""
        breadcrumb = []
        category = CategoryService.get_category_by_id(db, category_id)
        
        current = category
        while current:
            breadcrumb.insert(0, {
                "id": current.id,
                "name": current.name
            })
            if current.parent_id:
                current = db.query(Category).filter(Category.id == current.parent_id).first()
            else:
                current = None
        
        return breadcrumb
    
    @staticmethod
    def get_child_categories(db: Session, parent_id: int, active_only: bool = True) -> List[Category]:
        """Get direct child categories of a parent"""
        query = db.query(Category).filter(Category.parent_id == parent_id)
        if active_only:
            query = query.filter(Category.is_active == True)
        return query.order_by(Category.name).all()
    
    @staticmethod
    def get_popular_categories(
        db: Session, 
        limit: int = 6,
        sort_by: str = "events_count"
    ) -> List[dict]:
        """
        Get popular categories for dashboard (only root/parent categories)
        """
        now = get_current_utc()
        
        query = db.query(
            Category.id,
            Category.name,
            Category.icon,
            Category.color,
            Category.image_url,
            Category.parent_id,
            func.count(Event.id).label("events_count"),
            func.coalesce(func.sum(Booking.total_price), 0).label("total_bookings"),
            func.coalesce(func.sum(Booking.number_of_seats), 0).label("total_seats_booked"),
            func.coalesce(func.sum(Booking.total_price), 0).label("revenue")
        ).outerjoin(
            Event, Event.category_id == Category.id
        ).outerjoin(
            Booking, and_(
                Booking.event_id == Event.id,
                Booking.status == BookingStatus.ACTIVE
            )
        ).filter(
            Category.is_active == True,
            Event.status == EventStatus.UPCOMING,
            Event.event_date > now
        ).group_by(Category.id)
        
        if sort_by == "events_count":
            query = query.order_by(func.count(Event.id).desc())
        elif sort_by == "total_bookings":
            query = query.order_by(func.coalesce(func.sum(Booking.total_price), 0).desc())
        elif sort_by == "revenue":
            query = query.order_by(func.coalesce(func.sum(Booking.total_price), 0).desc())
        elif sort_by == "seats_booked":
            query = query.order_by(func.coalesce(func.sum(Booking.number_of_seats), 0).desc())
        else:
            query = query.order_by(func.count(Event.id).desc())
        
        results = query.limit(limit).all()
        
        # Get parent names for child categories
        result_list = []
        for r in results:
            parent_name = None
            if r.parent_id:
                parent = db.query(Category).filter(Category.id == r.parent_id).first()
                parent_name = parent.name if parent else None
            
            result_list.append({
                "id": r.id,
                "name": r.name,
                "icon": r.icon,
                "color": r.color,
                "image_url": r.image_url,
                "parent_name": parent_name,
                "events_count": r.events_count or 0,
                "total_bookings": float(r.total_bookings) if r.total_bookings else 0,
                "total_seats_booked": r.total_seats_booked or 0,
                "revenue": float(r.revenue) if r.revenue else 0
            })
        
        return result_list
    
    @staticmethod
    def get_category_stats(db: Session, category_id: int) -> dict:
        """Get detailed statistics for a specific category including children"""
        category = CategoryService.get_category_by_id(db, category_id)
        now = get_current_utc()
        
        # Get all subcategory IDs for event counting
        category_ids = [category_id]
        for child in category.children:
            category_ids.append(child.id)
            for grandchild in child.children:
                category_ids.append(grandchild.id)
        
        # Get event counts (including children)
        total_events = db.query(Event).filter(
            Event.category_id.in_(category_ids)
        ).count()
        
        upcoming_events = db.query(Event).filter(
            Event.category_id.in_(category_ids),
            Event.status == EventStatus.UPCOMING,
            Event.event_date > now
        ).count()
        
        completed_events = db.query(Event).filter(
            Event.category_id.in_(category_ids),
            Event.status == EventStatus.COMPLETED
        ).count()
        
        # Get booking stats (including children)
        booking_stats = db.query(
            func.coalesce(func.sum(Booking.total_price), 0).label("total_revenue"),
            func.coalesce(func.sum(Booking.number_of_seats), 0).label("total_seats_booked"),
            func.count(Booking.id).label("total_bookings")
        ).join(Event).filter(
            Event.category_id.in_(category_ids),
            Booking.status == BookingStatus.ACTIVE
        ).first()
        
        # Get parent name
        parent_name = None
        if category.parent_id:
            parent = db.query(Category).filter(Category.id == category.parent_id).first()
            parent_name = parent.name if parent else None
        
        return {
            "id": category.id,
            "name": category.name,
            "icon": category.icon,
            "color": category.color,
            "image_url": category.image_url,
            "parent_id": category.parent_id,
            "parent_name": parent_name,
            "level": category.level,
            "total_events": total_events,
            "upcoming_events": upcoming_events,
            "completed_events": completed_events,
            "total_bookings": booking_stats.total_bookings or 0,
            "total_seats_booked": booking_stats.total_seats_booked or 0,
            "total_revenue": float(booking_stats.total_revenue) if booking_stats.total_revenue else 0,
            "children_count": len(category.children)
        }
    
    @staticmethod
    def get_category_event_count(db: Session, category_id: int) -> int:
        """Get total number of upcoming events in a category (including children)"""
        now = get_current_utc()
        category = CategoryService.get_category_by_id(db, category_id)
        
        # Get all subcategory IDs
        category_ids = [category_id]
        for child in category.children:
            category_ids.append(child.id)
        
        return db.query(Event).filter(
            Event.category_id.in_(category_ids),
            Event.status == EventStatus.UPCOMING,
            Event.event_date > now
        ).count()
    
    @staticmethod
    def get_featured_categories(db: Session, limit: int = 4) -> List[Category]:
        """Get featured categories (random selection of root categories with images)"""
        categories = db.query(Category).filter(
            Category.is_active == True,
            Category.image_url.isnot(None),
            Category.parent_id.is_(None)  # Only root categories
        ).order_by(func.random()).limit(limit).all()
        
        return categories
    
    @staticmethod
    def get_ancestors(db: Session, category_id: int) -> List[Category]:
        """Get all ancestors of a category (parent, grandparent, etc.)"""
        ancestors = []
        category = CategoryService.get_category_by_id(db, category_id)
        
        current = category
        while current.parent_id:
            parent = db.query(Category).filter(Category.id == current.parent_id).first()
            if parent:
                ancestors.insert(0, parent)
                current = parent
            else:
                break
        
        return ancestors
    
    @staticmethod
    def get_descendants(db: Session, category_id: int) -> List[Category]:
        """Get all descendants of a category (children, grandchildren, etc.)"""
        descendants = []
        children = CategoryService.get_child_categories(db, category_id, active_only=False)
        
        for child in children:
            descendants.append(child)
            descendants.extend(CategoryService.get_descendants(db, child.id))
        
        return descendants