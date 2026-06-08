from fastapi import Query
from sqlalchemy.orm import Query as SQLQuery
from typing import Any, List, Tuple, TypeVar
from dataclasses import dataclass

T = TypeVar("T")


@dataclass
class PaginationParams:
    """
    Standard pagination parameters.
    Used across all endpoints that support pagination.
    """
    page: int
    limit: int

    @property
    def offset(self) -> int:
        """Calculate offset from page and limit"""
        return (self.page - 1) * self.limit


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    FastAPI dependency to extract pagination parameters from query.
    Usage: pagination: PaginationParams = Depends(get_pagination_params)
    """
    return PaginationParams(page=page, limit=limit)


def paginate_query(
    query: SQLQuery,
    params: PaginationParams
) -> Tuple[List[Any], int]:
    """
    Apply pagination to a SQLAlchemy query.
    Returns (items, total_count).

    Usage:
        items, total = paginate_query(query, params)
    """
    # Get total count before pagination
    total = query.count()

    # Apply offset and limit
    items = query.offset(params.offset).limit(params.limit).all()

    return items, total


def create_pagination_meta(
    total: int,
    page: int,
    limit: int
) -> dict:
    """
    Create pagination metadata for response.

    Returns:
        {
            "total": 100,
            "page": 1,
            "limit": 10,
            "total_pages": 10,
            "has_next": True,
            "has_previous": False
        }
    """
    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }