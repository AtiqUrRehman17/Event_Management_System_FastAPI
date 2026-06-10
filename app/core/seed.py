from sqlalchemy.orm import Session
from app.models.user import User
from app.models.category import Category
from app.core.enums import UserRole
from app.utils.auth_utils import hash_password
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def seed_admin(db: Session) -> None:
    """Create default admin user if no admin exists."""
    try:
        existing_admin = db.query(User).filter(
            User.role == UserRole.ADMIN
        ).first()

        if existing_admin:
            logger.info(
                f"Admin already exists: {existing_admin.username} "
                f"- Skipping seed"
            )
            return

        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            first_name=settings.ADMIN_FIRST_NAME,
            last_name=settings.ADMIN_LAST_NAME,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            phone=None,
            bio="System Administrator",
            timezone="UTC",
            profile_picture=None,
            oauth_provider=None,
            oauth_id=None
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        logger.info(
            f"Default admin created successfully - username: {admin.username}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed admin user: {str(e)}")
        raise


def seed_categories(db: Session) -> None:
    """Seed default categories with icons, colors, and images."""
    try:
        # Check if categories already exist
        existing_count = db.query(Category).count()
        if existing_count > 0:
            logger.info(f"Categories already exist ({existing_count} categories) - Skipping seed")
            return

        categories = [
            {
                "name": "Music Concerts",
                "description": "Live music concerts and performances from top artists around the world. Experience unforgettable nights with your favorite bands.",
                "icon": "fa-music",
                "color": "#3498db",
                "image_url": "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=400&h=300&fit=crop"
            },
            {
                "name": "Sports Events",
                "description": "Exciting sports events including football, basketball, tennis, and more. Cheer for your favorite teams live!",
                "icon": "fa-futbol",
                "color": "#2ecc71",
                "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=400&h=300&fit=crop"
            },
            {
                "name": "Workshops",
                "description": "Educational workshops and seminars to enhance your skills. Learn from industry experts and grow your career.",
                "icon": "fa-chalkboard-teacher",
                "color": "#9b59b6",
                "image_url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=400&h=300&fit=crop"
            },
            {
                "name": "Arts & Theatre",
                "description": "Art exhibitions, theatre performances, and cultural shows. Immerse yourself in creativity and culture.",
                "icon": "fa-palette",
                "color": "#e74c3c",
                "image_url": "https://images.unsplash.com/photo-1503095396549-807759245b35?w=400&h=300&fit=crop"
            },
            {
                "name": "Food & Drink",
                "description": "Food festivals, wine tasting, and culinary experiences. Explore delicious cuisines and drinks.",
                "icon": "fa-utensils",
                "color": "#f39c12",
                "image_url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop"
            },
            {
                "name": "Business & Networking",
                "description": "Business conferences, networking events, and professional meetups. Connect with industry leaders and grow your network.",
                "icon": "fa-briefcase",
                "color": "#1abc9c",
                "image_url": "https://images.unsplash.com/photo-1556761175-b413da4baf72?w=400&h=300&fit=crop"
            },
            {
                "name": "Technology",
                "description": "Tech conferences, hackathons, and coding workshops. Stay updated with the latest technology trends.",
                "icon": "fa-microchip",
                "color": "#34495e",
                "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&h=300&fit=crop"
            },
            {
                "name": "Health & Wellness",
                "description": "Yoga sessions, meditation workshops, and wellness retreats. Rejuvenate your mind and body.",
                "icon": "fa-heartbeat",
                "color": "#e84393",
                "image_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400&h=300&fit=crop"
            },
            {
                "name": "Family & Kids",
                "description": "Family-friendly events, kids activities, and entertainment for all ages. Create wonderful memories with your loved ones.",
                "icon": "fa-child",
                "color": "#f1c40f",
                "image_url": "https://images.unsplash.com/photo-1513159448701-2e674de46f97?w=400&h=300&fit=crop"
            },
            {
                "name": "Outdoor & Adventure",
                "description": "Hiking, camping, and outdoor adventure activities. Explore nature and enjoy thrilling experiences.",
                "icon": "fa-hiking",
                "color": "#27ae60",
                "image_url": "https://images.unsplash.com/photo-1551632811-561732d1e306?w=400&h=300&fit=crop"
            }
        ]

        for cat_data in categories:
            category = Category(**cat_data)
            db.add(category)
        
        db.commit()
        
        logger.info(f"Successfully seeded {len(categories)} categories with icons, colors, and images")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed categories: {str(e)}")
        raise


def seed_sample_events(db: Session) -> None:
    """Seed sample events for testing (optional)."""
    try:
        from app.models.event import Event
        from app.core.enums import EventStatus
        from datetime import datetime, timedelta
        
        # Check if events already exist
        existing_count = db.query(Event).count()
        if existing_count > 0:
            logger.info(f"Events already exist ({existing_count} events) - Skipping seed")
            return
        
        # Get admin user
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin:
            logger.warning("No admin found - skipping event seeding")
            return
        
        # Get categories
        categories = db.query(Category).all()
        if not categories:
            logger.warning("No categories found - skipping event seeding")
            return
        
        now = datetime.utcnow()
        
        events = [
            {
                "title": "Summer Rock Festival 2024",
                "description": "Join us for an amazing rock concert featuring top bands from around the world. Get ready for an unforgettable night of music!",
                "location": "Central Park, New York, NY",
                "event_date": now + timedelta(days=30),
                "total_seats": 500,
                "available_seats": 500,
                "price": 89.99,
                "status": EventStatus.UPCOMING,
                "category_id": next((c.id for c in categories if "Music" in c.name), categories[0].id),
                "image_url": "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?w=800",
                "created_by": admin.id
            },
            {
                "title": "Basketball Championship Final",
                "description": "Witness the exciting final match of the season! Top teams compete for the championship trophy.",
                "location": "Madison Square Garden, New York, NY",
                "event_date": now + timedelta(days=45),
                "total_seats": 1000,
                "available_seats": 1000,
                "price": 120.00,
                "status": EventStatus.UPCOMING,
                "category_id": next((c.id for c in categories if "Sports" in c.name), categories[0].id),
                "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800",
                "created_by": admin.id
            },
            {
                "title": "Python Programming Workshop",
                "description": "Learn Python from scratch in this hands-on workshop. Perfect for beginners and intermediate programmers.",
                "location": "Online (Zoom)",
                "event_date": now + timedelta(days=15),
                "total_seats": 100,
                "available_seats": 100,
                "price": 49.99,
                "status": EventStatus.UPCOMING,
                "category_id": next((c.id for c in categories if "Workshop" in c.name or "Technology" in c.name), categories[0].id),
                "image_url": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800",
                "created_by": admin.id
            },
            {
                "title": "Art Exhibition: Modern Masters",
                "description": "Explore stunning artworks from contemporary artists. A must-see exhibition for art lovers.",
                "location": "Metropolitan Museum of Art, New York, NY",
                "event_date": now + timedelta(days=60),
                "total_seats": 300,
                "available_seats": 300,
                "price": 25.00,
                "status": EventStatus.UPCOMING,
                "category_id": next((c.id for c in categories if "Arts" in c.name), categories[0].id),
                "image_url": "https://images.unsplash.com/photo-1503095396549-807759245b35?w=800",
                "created_by": admin.id
            },
            {
                "title": "Wine & Dine Festival",
                "description": "Experience the finest wines and gourmet cuisine from top chefs. A culinary journey you won't forget!",
                "location": "Jacob K. Javits Convention Center, New York, NY",
                "event_date": now + timedelta(days=75),
                "total_seats": 200,
                "available_seats": 200,
                "price": 150.00,
                "status": EventStatus.UPCOMING,
                "category_id": next((c.id for c in categories if "Food" in c.name), categories[0].id),
                "image_url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800",
                "created_by": admin.id
            },
            {
                "title": "Tech Innovation Summit 2024",
                "description": "Join industry leaders to discuss the future of technology. AI, Blockchain, Cloud Computing, and more.",
                "location": "Convention Center, San Francisco, CA",
                "event_date": now + timedelta(days=90),
                "total_seats": 800,
                "available_seats": 800,
                "price": 299.00,
                "status": EventStatus.UPCOMING,
                "category_id": next((c.id for c in categories if "Technology" in c.name or "Business" in c.name), categories[0].id),
                "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
                "created_by": admin.id
            }
        ]
        
        for event_data in events:
            event = Event(**event_data)
            db.add(event)
        
        db.commit()
        logger.info(f"Successfully seeded {len(events)} sample events")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed sample events: {str(e)}")
        raise


def seed_all(db: Session) -> None:
    """Run all seed functions."""
    logger.info("Starting database seeding...")
    
    # Seed admin user
    seed_admin(db)
    
    # Seed categories (must come before events)
    seed_categories(db)
    
    # Seed sample events (optional - comment out if not needed)
    seed_sample_events(db)
    
    logger.info("Database seeding completed successfully!")