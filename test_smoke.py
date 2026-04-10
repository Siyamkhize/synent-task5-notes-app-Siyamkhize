import pytest
from app import create_app
from models import db

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_page(client):
    """Test if home page redirects to login."""
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_login_page_loads(client):
    """Test if login page loads correctly."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data

def test_register_page_loads(client):
    """Test if register page loads correctly."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Register" in response.data
