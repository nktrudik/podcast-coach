from types import TracebackType

import pytest
from app.main import app
from fastapi.testclient import TestClient


class FakeConnection:
    """Minimal context manager used by the health endpoint test."""

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def execute(self, query: str) -> "FakeConnection":
        assert query == "SELECT 1"
        return self

    def fetchone(self) -> dict[str, int]:
        return {"ok": 1}


def test_health_endpoint_returns_database_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Health endpoint reports application and database availability."""

    def fake_get_connection() -> FakeConnection:
        return FakeConnection()

    monkeypatch.setattr("app.api.routes.health.get_connection", fake_get_connection)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "ok", "database": "ok"}
