from typing import Any, Optional, Dict, List
from fastapi.responses import JSONResponse
from fastapi import status
from datetime import datetime, date
from enum import Enum
import json


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles:
    - datetime objects → ISO format string
    - date objects → ISO format string
    - Enum values → their string/value representation
    - Any other non-serializable object → str()
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def serialize(data: Any) -> Any:
    """
    Recursively serialize data using CustomJSONEncoder.
    Converts the data to JSON string and back to dict
    so JSONResponse can handle it cleanly.
    """
    if data is None:
        return None
    # Serialize to JSON string using custom encoder
    # then parse back to Python dict/list
    json_str = json.dumps(data, cls=CustomJSONEncoder)
    return json.loads(json_str)


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    meta: Optional[Dict] = None
) -> JSONResponse:
    """
    Standard success response formatter.
    Handles datetime, Enum, and other non-serializable types.
    """
    response_body = {
        "success": True,
        "message": message,
        "data": serialize(data)
    }

    if meta:
        response_body["meta"] = serialize(meta)

    return JSONResponse(
        status_code=status_code,
        content=response_body
    )


def error_response(
    message: str = "Error",
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    details: Optional[Any] = None
) -> JSONResponse:
    """
    Standard error response formatter.
    """
    response_body = {
        "success": False,
        "message": message,
        "error_code": error_code
    }

    if details:
        response_body["details"] = serialize(details)

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
    Paginated response formatter.
    Calculates total_pages automatically.
    """
    return success_response(
        data=serialize(items),
        message=message,
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if total > 0 else 0
        }
    )