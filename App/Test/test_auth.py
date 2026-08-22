import pytest
from fastapi.testclient import TestClient
from App.app import app
from App.routes.auth.helper import (
    create_access_token,
    generate_password_hash,
    validate_password,
    create_reset_token,
    verify_reset_token,
)

client = TestClient(app)
Name = "name"
token = None
hash_password = None


# ====================( Routes )====================
# def test_login_success():
#     response = client.post(
#         "/v1/api/auth/login",
#         json={"email": "bahaamo56179011@gmail.com", "password": "B@haa56179011"},
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert "access_token" in data
#     print(data)


# ====================( Routes )====================


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
