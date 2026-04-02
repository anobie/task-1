from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_health() -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert response.headers.get("X-Request-ID")


def test_request_id_is_preserved_when_provided() -> None:
    custom_request_id = "req-test-123"
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": custom_request_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_request_id
