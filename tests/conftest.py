import pytest

from clear import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "SECRET_KEY": "test-key-only", "DATABASE": str(tmp_path / "test.sqlite3")})


@pytest.fixture
def client(app):
    client = app.test_client()
    client.get("/")
    return client


@pytest.fixture
def csrf(client):
    with client.session_transaction() as session:
        return {"X-CSRF-Token": session["csrf"]}
