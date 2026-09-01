import pytest

from App.Test.conftest import auth_header, create_test_user, login_user


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

    res = await client.get(
        "/v1/api/auth/check",
        headers=auth_header(token),
    )
    assert res.status_code == 200