from fastapi.testclient import TestClient

from App.app import app
from App.routes.auth.helper import (
    create_access_token,
    create_reset_token,
    generate_password_hash,
    validate_password,
    verify_reset_token,
)
import pytest

client = TestClient(app)
Name = "name"
token = None
jwt = None
hash_password = None

ROUTE_AUTH = "/v1/api/auth"


# ====================( tools )====================
def test_access_token_creation():
    jwt = create_access_token({"name": "None"})
    assert jwt != None


def test_generate_password_hash():
    global hash_password
    text_password: str = "pass123"
    hash_password = generate_password_hash(text_password)
    assert hash_password != None


def test_password_validation_success():
    is_password = validate_password(hashedPassword=hash_password, password="pass123")
    assert is_password == True


def test_generate_reset_token():
    global token
    create_token = create_reset_token(Name)
    assert create_token != None
    token = create_token


def test_verify_reset_token_validity():
    is_token = verify_reset_token(token)
    assert is_token == "name"


# ====================( tools )====================


# ====================( Routes )====================
def test_login_success():
    global jwt
    response = client.post(
        "/v1/api/auth/login",
        json={"email": "user2@example.com", "password": "Strin&st0123"},
    )
    assert response.status_code == 200
    data = response.json()
    jwt = data["access_token"]
    assert "access_token" in data
    print(jwt)


def test_validate_jwt_access():
    headers = {"Authorization": f"Bearer {jwt}"}

    response = client.get(ROUTE_AUTH + "/check", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["Info"]["Email"] == "user2@example.com"


def test_access_dashboard_without_token():
    response = client.get(ROUTE_AUTH + "/check")
    assert response.status_code == 401


# ====================( Routes )====================
