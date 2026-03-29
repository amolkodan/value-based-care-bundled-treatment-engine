from __future__ import annotations

from fastapi.testclient import TestClient

from vbc_claims.api.main import app


def test_api_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "vbc-claims-api"

