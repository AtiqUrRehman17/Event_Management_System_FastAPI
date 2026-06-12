import pytest
from fastapi import status
from app.utils.response import (
    success_response,
    error_response,
    paginated_response,
    serialize
)
from datetime import datetime
from enum import Enum


@pytest.mark.unit
class TestSerialize:

    def test_serialize_none(self):
        """None should return None"""
        assert serialize(None) is None

    def test_serialize_datetime(self):
        """Datetime should be converted to ISO string"""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = serialize({"created_at": dt})
        assert isinstance(result["created_at"], str)
        assert "2024" in result["created_at"]

    def test_serialize_enum(self):
        """Enum should be converted to its value"""
        class TestEnum(Enum):
            ACTIVE = "active"

        result = serialize({"status": TestEnum.ACTIVE})
        assert result["status"] == "active"

    def test_serialize_plain_dict(self):
        """Plain dict should pass through unchanged"""
        data = {"key": "value", "number": 42}
        result = serialize(data)
        assert result == data

    def test_serialize_list(self):
        """List should be serialized correctly"""
        data = [{"id": 1}, {"id": 2}]
        result = serialize(data)
        assert len(result) == 2
        assert result[0]["id"] == 1


@pytest.mark.unit
class TestSuccessResponse:

    def test_returns_json_response(self):
        """Should return a JSONResponse"""
        from fastapi.responses import JSONResponse
        response = success_response(data={"id": 1}, message="OK")
        assert isinstance(response, JSONResponse)

    def test_success_is_true(self):
        """success field should be True"""
        response = success_response(data={"id": 1}, message="OK")
        body = response.body
        import json
        content = json.loads(body)
        assert content["success"] is True

    def test_message_in_response(self):
        """Message should be in response"""
        import json
        response = success_response(data={}, message="Created successfully")
        content = json.loads(response.body)
        assert content["message"] == "Created successfully"

    def test_default_status_code_200(self):
        """Default status code should be 200"""
        response = success_response(data={})
        assert response.status_code == 200

    def test_custom_status_code(self):
        """Custom status code should be respected"""
        response = success_response(
            data={},
            status_code=status.HTTP_201_CREATED
        )
        assert response.status_code == 201

    def test_data_in_response(self):
        """Data should be in response body"""
        import json
        response = success_response(data={"id": 1, "name": "test"})
        content = json.loads(response.body)
        assert content["data"]["id"] == 1
        assert content["data"]["name"] == "test"

    def test_none_data(self):
        """None data should be handled"""
        import json
        response = success_response(data=None)
        content = json.loads(response.body)
        assert content["data"] is None

    def test_meta_included_when_provided(self):
        """Meta should be included when provided"""
        import json
        meta = {"total": 100, "page": 1}
        response = success_response(data=[], meta=meta)
        content = json.loads(response.body)
        assert "meta" in content
        assert content["meta"]["total"] == 100


@pytest.mark.unit
class TestErrorResponse:

    def test_success_is_false(self):
        """success field should be False"""
        import json
        response = error_response(message="Error occurred")
        content = json.loads(response.body)
        assert content["success"] is False

    def test_message_in_response(self):
        """Error message should be in response"""
        import json
        response = error_response(message="Something went wrong")
        content = json.loads(response.body)
        assert content["message"] == "Something went wrong"

    def test_error_code_in_response(self):
        """Error code should be in response"""
        import json
        response = error_response(
            message="Not found",
            error_code="NOT_FOUND"
        )
        content = json.loads(response.body)
        assert content["error_code"] == "NOT_FOUND"

    def test_default_status_code_400(self):
        """Default status code should be 400"""
        response = error_response(message="Bad request")
        assert response.status_code == 400

    def test_custom_status_code(self):
        """Custom status code should be respected"""
        response = error_response(
            message="Not found",
            status_code=404
        )
        assert response.status_code == 404

    def test_details_included_when_provided(self):
        """Details should be included when provided"""
        import json
        response = error_response(
            message="Validation failed",
            details=["field1 is required"]
        )
        content = json.loads(response.body)
        assert "details" in content


@pytest.mark.unit
class TestPaginatedResponse:

    def test_returns_success_true(self):
        """Should return success True"""
        import json
        response = paginated_response(
            items=[{"id": 1}],
            total=1,
            page=1,
            limit=10
        )
        content = json.loads(response.body)
        assert content["success"] is True

    def test_includes_meta(self):
        """Should include pagination meta"""
        import json
        response = paginated_response(
            items=[],
            total=100,
            page=2,
            limit=10
        )
        content = json.loads(response.body)
        assert "meta" in content
        assert content["meta"]["total"] == 100
        assert content["meta"]["page"] == 2
        assert content["meta"]["limit"] == 10

    def test_includes_items_in_data(self):
        """Should include items in data field"""
        import json
        items = [{"id": 1}, {"id": 2}]
        response = paginated_response(
            items=items,
            total=2,
            page=1,
            limit=10
        )
        content = json.loads(response.body)
        assert len(content["data"]) == 2

    def test_custom_message(self):
        """Should include custom message"""
        import json
        response = paginated_response(
            items=[],
            total=0,
            page=1,
            limit=10,
            message="Users retrieved"
        )
        content = json.loads(response.body)
        assert content["message"] == "Users retrieved"