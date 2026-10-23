"""API tests for authentication and profile routes."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(client):
    """Assert that the login handler returns HTTP 401 when credentials do not match a user."""
    response = await client.post(
        "/api/auth/login",
        data={"username": "missing-user", "password": "bad-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_boot_rejects_invalid_credentials(client):
    """Assert that the boot endpoint enforces the same credential checks as the login endpoint."""
    response = await client.post(
        "/api/auth/boot",
        data={"username": "missing-user", "password": "bad-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_and_boot_return_shell_payload(client, authenticated_user):
    """Login/bootstrap responses carry the shared access state needed before rendering."""
    login_response = await client.post(
        "/api/auth/login",
        data={"username": authenticated_user.username, "password": "secret123"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    for key in (
        "user",
        "permissions",
        "sidebar",
        "allowed_dashboards",
        "workflow_states",
        "branding_settings",
        "workspace_context",
        "feature_flags",
    ):
        assert key in login_payload
    assert login_payload["workspace_context"]["capabilities"]["is_system_admin"] is True
    assert login_payload["permissions"]

    boot_response = await client.post(
        "/api/auth/boot",
        data={"username": authenticated_user.username, "password": "secret123"},
    )
    assert boot_response.status_code == 200
    boot_payload = boot_response.json()
    assert boot_payload["access_token"]
    assert boot_payload["workspace_context"] == login_payload["workspace_context"]

    restored_response = await client.get(
        "/api/auth/boot",
        headers={"Authorization": f"Bearer {boot_payload['access_token']}"},
    )
    assert restored_response.status_code == 200
    restored_payload = restored_response.json()
    assert restored_payload["user"]["id"] == authenticated_user.id
    assert restored_payload["workspace_context"] == boot_payload["workspace_context"]

    refresh_response = await client.post("/api/auth/refresh", json={})
    assert refresh_response.status_code == 200
    refreshed_token = refresh_response.json()["access_token"]
    assert refreshed_token

    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["user"]["id"] == authenticated_user.id
    assert me_payload["new_token"]

    restored_after_refresh = await client.get(
        "/api/auth/boot",
        headers={"Authorization": f"Bearer {refreshed_token}"},
    )
    assert restored_after_refresh.status_code == 200
    assert restored_after_refresh.json()["user"]["id"] == authenticated_user.id


@pytest.mark.asyncio
async def test_refresh_requires_refresh_token(client):
    """Assert that the refresh endpoint rejects requests that provide neither a cookie nor a request-body token."""
    response = await client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing refresh token"


@pytest.mark.asyncio
async def test_validate_requires_bearer_header(client):
    """Assert that token validation returns HTTP 401 when the authorization header is missing."""
    response = await client.get("/api/auth/validate")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or invalid authorization header"


@pytest.mark.asyncio
async def test_auth_me_requires_access_or_refresh_token(client):
    """Assert that the auth bootstrap probe returns HTTP 401 when neither access nor refresh authentication is present."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_returns_authenticated_user_payload(authenticated_client, authenticated_user):
    """Assert that the profile handler returns the current user payload when authentication is resolved through the dependency override."""
    response = await authenticated_client.get("/api/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["id"] == authenticated_user.id
    assert payload["data"]["username"] == authenticated_user.username
