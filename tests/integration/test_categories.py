import pytest


@pytest.mark.integration
@pytest.mark.categories
class TestGetCategories:

    def test_get_all_categories(self, client, categories_url, test_category):
        """Should return all categories"""
        response = client.get(f"{categories_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_get_categories_as_tree(self, client, categories_url, test_category):
        """Should return categories as tree by default"""
        response = client.get(f"{categories_url}/")
        assert response.status_code == 200

    def test_get_categories_as_flat_list(self, client, categories_url, test_category):
        """Should return flat list when flat=true"""
        response = client.get(f"{categories_url}/?flat=true")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)

    def test_get_category_tree(self, client, categories_url, test_category):
        """Should return category tree"""
        response = client.get(f"{categories_url}/tree")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_popular_categories(self, client, categories_url):
        """Should return popular categories"""
        response = client.get(f"{categories_url}/popular")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_featured_categories(self, client, categories_url):
        """Should return featured categories"""
        response = client.get(f"{categories_url}/featured")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.categories
class TestGetCategoryById:

    def test_get_category_success(self, client, categories_url, test_category):
        """Should return category by ID"""
        response = client.get(f"{categories_url}/{test_category.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == test_category.id
        assert data["data"]["name"] == "Test Category"

    def test_get_nonexistent_category(self, client, categories_url):
        """Should return 404 for non-existent category"""
        response = client.get(f"{categories_url}/99999")
        assert response.status_code == 404

    def test_get_category_with_children(self, client, categories_url, test_category):
        """Should return category with children when requested"""
        response = client.get(
            f"{categories_url}/{test_category.id}?include_children=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert "children" in data["data"]


@pytest.mark.integration
@pytest.mark.categories
class TestCreateCategory:

    def test_create_category_as_admin(self, client, categories_url, admin_auth_headers):
        """Admin should create category successfully"""
        response = client.post(f"{categories_url}/", json={
            "name": "New Category",
            "description": "A new test category",
            "icon": "fa-star",
            "color": "#e74c3c"
        }, headers=admin_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Category"

    def test_create_category_as_user(self, client, categories_url, user_auth_headers):
        """Regular user should not create category"""
        response = client.post(f"{categories_url}/", json={
            "name": "New Category",
            "description": "Test"
        }, headers=user_auth_headers)
        assert response.status_code == 403

    def test_create_duplicate_category(self, client, categories_url, admin_auth_headers, test_category):
        """Should fail with duplicate category name"""
        response = client.post(f"{categories_url}/", json={
            "name": "Test Category",  # Already exists
            "description": "Duplicate"
        }, headers=admin_auth_headers)
        assert response.status_code == 400

    def test_create_category_with_parent(self, client, categories_url, admin_auth_headers, test_category):
        """Should create child category with parent"""
        response = client.post(f"{categories_url}/", json={
            "name": "Child Category",
            "description": "A child category",
            "parent_id": test_category.id
        }, headers=admin_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["parent_id"] == test_category.id

    def test_create_category_invalid_color(self, client, categories_url, admin_auth_headers):
        """Should fail with invalid hex color"""
        response = client.post(f"{categories_url}/", json={
            "name": "Bad Color Category",
            "color": "not-a-color"
        }, headers=admin_auth_headers)
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.categories
class TestUpdateCategory:

    def test_update_category_success(self, client, categories_url, admin_auth_headers, test_category):
        """Admin should update category"""
        response = client.put(f"{categories_url}/{test_category.id}", json={
            "name": "Updated Category",
            "description": "Updated description"
        }, headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Category"

    def test_update_category_as_user(self, client, categories_url, user_auth_headers, test_category):
        """Regular user should not update category"""
        response = client.put(f"{categories_url}/{test_category.id}", json={
            "name": "Updated"
        }, headers=user_auth_headers)
        assert response.status_code == 403

    def test_update_nonexistent_category(self, client, categories_url, admin_auth_headers):
        """Should return 404 for non-existent category"""
        response = client.put(f"{categories_url}/99999", json={
            "name": "Updated"
        }, headers=admin_auth_headers)
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.categories
class TestDeleteCategory:

    def test_delete_category_as_admin(self, client, categories_url, admin_auth_headers, test_category):
        """Admin should delete category"""
        response = client.delete(
            f"{categories_url}/{test_category.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_category_as_user(self, client, categories_url, user_auth_headers, test_category):
        """Regular user should not delete category"""
        response = client.delete(
            f"{categories_url}/{test_category.id}",
            headers=user_auth_headers
        )
        assert response.status_code == 403

    def test_delete_nonexistent_category(self, client, categories_url, admin_auth_headers):
        """Should return 404 for non-existent category"""
        response = client.delete(
            f"{categories_url}/99999",
            headers=admin_auth_headers
        )
        assert response.status_code == 404