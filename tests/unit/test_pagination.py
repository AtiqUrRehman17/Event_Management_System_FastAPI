import pytest
from unittest.mock import MagicMock
from app.pagination.pagination import (
    PaginationParams,
    paginate_query,
    create_pagination_meta
)


@pytest.mark.unit
class TestPaginationParams:

    def test_offset_first_page(self):
        """Page 1 should have offset 0"""
        params = PaginationParams(page=1, limit=10)
        assert params.offset == 0

    def test_offset_second_page(self):
        """Page 2 should have offset equal to limit"""
        params = PaginationParams(page=2, limit=10)
        assert params.offset == 10

    def test_offset_third_page(self):
        """Page 3 should have offset 2 * limit"""
        params = PaginationParams(page=3, limit=10)
        assert params.offset == 20

    def test_offset_with_different_limit(self):
        """Offset should calculate correctly with different limits"""
        params = PaginationParams(page=3, limit=25)
        assert params.offset == 50

    def test_stores_page_and_limit(self):
        """Should store page and limit correctly"""
        params = PaginationParams(page=5, limit=20)
        assert params.page == 5
        assert params.limit == 20


@pytest.mark.unit
class TestPaginateQuery:

    def test_returns_items_and_total(self):
        """Should return tuple of (items, total)"""
        mock_query = MagicMock()
        mock_query.count.return_value = 100
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = ["item1", "item2"]

        params = PaginationParams(page=1, limit=2)
        items, total = paginate_query(mock_query, params)

        assert total == 100
        assert items == ["item1", "item2"]

    def test_calls_correct_offset(self):
        """Should call offset with correct value"""
        mock_query = MagicMock()
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        params = PaginationParams(page=3, limit=10)
        paginate_query(mock_query, params)

        mock_query.offset.assert_called_with(20)

    def test_calls_correct_limit(self):
        """Should call limit with correct value"""
        mock_query = MagicMock()
        mock_query.count.return_value = 50
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        params = PaginationParams(page=1, limit=15)
        paginate_query(mock_query, params)

        mock_query.limit.assert_called_with(15)


@pytest.mark.unit
class TestCreatePaginationMeta:

    def test_first_page_no_previous(self):
        """First page should have no previous"""
        meta = create_pagination_meta(total=100, page=1, limit=10)
        assert meta["has_previous"] is False

    def test_last_page_no_next(self):
        """Last page should have no next"""
        meta = create_pagination_meta(total=100, page=10, limit=10)
        assert meta["has_next"] is False

    def test_middle_page_has_both(self):
        """Middle page should have both next and previous"""
        meta = create_pagination_meta(total=100, page=5, limit=10)
        assert meta["has_next"] is True
        assert meta["has_previous"] is True

    def test_total_pages_calculation(self):
        """Should calculate total pages correctly"""
        meta = create_pagination_meta(total=100, page=1, limit=10)
        assert meta["total_pages"] == 10

    def test_total_pages_with_remainder(self):
        """Should round up total pages when there's a remainder"""
        meta = create_pagination_meta(total=101, page=1, limit=10)
        assert meta["total_pages"] == 11

    def test_empty_results(self):
        """Should handle empty results"""
        meta = create_pagination_meta(total=0, page=1, limit=10)
        assert meta["total_pages"] == 0
        assert meta["has_next"] is False
        assert meta["has_previous"] is False

    def test_returns_all_required_keys(self):
        """Should return all required metadata keys"""
        meta = create_pagination_meta(total=50, page=2, limit=10)
        assert "total" in meta
        assert "page" in meta
        assert "limit" in meta
        assert "total_pages" in meta
        assert "has_next" in meta
        assert "has_previous" in meta

    def test_values_match_input(self):
        """Returned values should match input"""
        meta = create_pagination_meta(total=50, page=2, limit=10)
        assert meta["total"] == 50
        assert meta["page"] == 2
        assert meta["limit"] == 10