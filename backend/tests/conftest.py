import pytest
from flask_jwt_extended import create_access_token, set_access_cookies
from argon2 import PasswordHasher
from app import create_app
from app.extensions import db
from app.models import User

@pytest.fixture()
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_COOKIE_SECURE": False,
        "RATELIMIT_ENABLED": False,
    })
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

def create_user(email, role):
    user = User(email=email, full_name=email, role=role, password_hash=PasswordHasher().hash("ValidPassword123!"))
    db.session.add(user)
    db.session.commit()
    return user

def auth_client(app, user):
    client = app.test_client()
    with app.app_context():
        response = app.response_class()
        set_access_cookies(response, create_access_token(identity=user.id, additional_claims={"sv":user.session_version}))
        for cookie in response.headers.getlist("Set-Cookie"):
            client.set_cookie(cookie.split("=", 1)[0], cookie.split("=", 1)[1].split(";", 1)[0])
    return client

def csrf(client):
    token = client.get_cookie("csrf_access_token")
    return {"X-CSRF-TOKEN": token.value} if token else {}
