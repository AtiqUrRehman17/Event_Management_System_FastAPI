# tests/fixtures/category_fixtures.py


def get_valid_category_data():
    """Valid category creation data"""
    return {
        "name": "Fixture Category",
        "description": "A test category from fixtures",
        "icon": "fa-star",
        "color": "#3498db"
    }


def get_valid_category_with_image():
    """Valid category data with image URL"""
    return {
        "name": "Fixture Category With Image",
        "description": "A test category with image",
        "icon": "fa-image",
        "color": "#2ecc71",
        "image_url": "https://example.com/test-image.jpg"
    }


def get_valid_child_category_data(parent_id: int):
    """Valid child category data"""
    return {
        "name": "Fixture Child Category",
        "description": "A child test category",
        "icon": "fa-child",
        "color": "#e74c3c",
        "parent_id": parent_id
    }


def get_valid_grandchild_category_data(parent_id: int):
    """Valid grandchild category data"""
    return {
        "name": "Fixture Grandchild Category",
        "description": "A grandchild test category",
        "icon": "fa-circle",
        "color": "#9b59b6",
        "parent_id": parent_id
    }


def get_category_data_missing_name():
    """Invalid category data with missing name"""
    return {
        "description": "Missing name category",
        "icon": "fa-tag",
        "color": "#3498db"
    }


def get_category_data_invalid_color():
    """Invalid category data with bad hex color"""
    return {
        "name": "Bad Color Category",
        "description": "Invalid color",
        "icon": "fa-tag",
        "color": "not-a-color"
    }


def get_category_data_short_name():
    """Invalid category data with too short name"""
    return {
        "name": "A",
        "description": "Short name",
        "icon": "fa-tag",
        "color": "#3498db"
    }


def get_category_update_data():
    """Valid category update data"""
    return {
        "name": "Updated Category Name",
        "description": "Updated description",
        "color": "#e74c3c"
    }


def get_category_update_icon():
    """Category update with new icon"""
    return {
        "icon": "fa-music"
    }


def get_category_deactivate_data():
    """Category update to deactivate"""
    return {
        "is_active": False
    }


def get_category_activate_data():
    """Category update to activate"""
    return {
        "is_active": True
    }


def get_multiple_categories_data():
    """List of multiple valid categories"""
    return [
        {
            "name": "Music Events",
            "description": "Live music and concerts",
            "icon": "fa-music",
            "color": "#3498db"
        },
        {
            "name": "Sports Events",
            "description": "Sports and athletics",
            "icon": "fa-futbol",
            "color": "#2ecc71"
        },
        {
            "name": "Tech Events",
            "description": "Technology conferences",
            "icon": "fa-microchip",
            "color": "#9b59b6"
        },
        {
            "name": "Food Events",
            "description": "Food and culinary experiences",
            "icon": "fa-utensils",
            "color": "#f39c12"
        },
        {
            "name": "Art Events",
            "description": "Art and culture",
            "icon": "fa-palette",
            "color": "#e74c3c"
        }
    ]


def get_popular_categories_params():
    """Parameters for popular categories endpoint"""
    return {
        "limit": 6,
        "sort_by": "events_count"
    }


def get_popular_categories_by_revenue():
    """Parameters for popular categories by revenue"""
    return {
        "limit": 4,
        "sort_by": "revenue"
    }