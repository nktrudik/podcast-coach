from app.main import app


def test_openapi_schema_contains_versioned_video_job_contract() -> None:
    """OpenAPI includes the versioned video job endpoints and response fields."""
    schema = app.openapi()
    paths = schema["paths"]
    response_schema = schema["components"]["schemas"]["UploadVideoResponse"]

    assert "/api/v1/videos" in paths
    assert "/api/v1/chat/message" in paths
    assert "job_id" in response_schema["properties"]
    assert "status" in response_schema["properties"]
