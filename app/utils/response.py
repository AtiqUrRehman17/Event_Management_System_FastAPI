from typing import Any, Optional, Dict, List
from fastapi.responses import JSONResponse
from fastapi import status


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    meta: Optional[Dict] = None
) -> JSONResponse:
    """
    Standard success response formatter
    """
    response_body = {
        "success": True,
        "message": message,
        "data": data
    }
    
    if meta:
        response_body["meta"] = meta
    
    return JSONResponse(
        status_code=status_code,
        content=response_body
    )


def error_response(
    message: str = "Error",
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Dict] = None
) -> JSONResponse:
    """
    Standard error response formatter
    """
    response_body = {
        "success": False,
        "message": message,
        "error_code": error_code
    }
    
    if details:
        response_body["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=response_body
    )


def paginated_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int,
    message: str = "Success"
) -> JSONResponse:
    """
    Paginated response formatter
    """
    return success_response(
        data=items,
        message=message,
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )