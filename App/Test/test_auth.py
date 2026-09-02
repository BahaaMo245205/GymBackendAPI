import pytest

from App.Test.conftest import (
    auth_header,
    create_test_user,
    login_user,
    forgot_password,
    reset_password,
)
from App.routes.auth.helper import (
    create_access_token,
    create_reset_token,
    generate_password_hash,
    validate_password,
    verify_reset_token,
)

Name = "name"
token = None


@pytest.mark.asyncio
async def test_login_invalid(client):
    res = await client.post(
        "/v1/api/auth/login",
        json={"email": "no@email.com", "password": "wrongpass"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_register_and_login(client):
    await create_test_user(
        client,
        username="alias",
        email="alias_ci@email.com",
        password="Test@12345678",
    )
    token = await login_user(
        client,
        email="alias_ci@email.com",
        password="Test@12345678",
    )
    assert token


@pytest.mark.asyncio
async def test_forgot_password(client):
    response = await forgot_password(client, email="test@example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_reset_password(client):
    await create_test_user(
        client,
        username="alias",
        email="alias_ci@email.com",
        password="Test@12345678",
    )
    response = await reset_password(client, "B@haa2025", "B@haa2025")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


# =====================(helpers)================
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


# =====================(helpers)================
