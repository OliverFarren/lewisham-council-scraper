from fastapi.testclient import TestClient

from lewisham_server.main import app

client = TestClient(app)


def test_bins_placeholder() -> None:
    response = client.get("/bins/")
    assert response.status_code == 200
    assert response.json() == {"message": "bins endpoint placeholder"}
