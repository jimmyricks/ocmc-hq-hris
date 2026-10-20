"""Comprehensive API tests for the generic entity contract (Task 1)."""

from __future__ import annotations

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _create_tables(db_engine):
    """Create and drop tables for every test so the function-scoped SQLite DB is clean."""
    from app.core.database import Base

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_get_meta_list_and_detail(superuser_client):
    """Assert /api/meta lists entities and /api/meta/{entity} returns field metadata."""
    list_resp = await superuser_client.get("/api/meta")
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["status"] == "success"
    assert isinstance(list_payload["data"], list)
    names = {e["name"] for e in list_payload["data"]}
    assert "role" in names
    assert "user" in names

    detail_resp = await superuser_client.get("/api/meta/role")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload["status"] == "success"
    assert detail_payload["data"]["name"] == "role"
    assert "fields" in detail_payload["data"]
    field_keys = {f["key"] for f in detail_payload["data"]["fields"]}
    assert "name" in field_keys
    assert "description" in field_keys
    assert "is_active" in field_keys


@pytest.mark.asyncio
async def test_meta_detail_returns_error_for_unknown_entity(superuser_client):
    """Assert /api/meta/{entity} returns a controlled error for unknown entities."""
    resp = await superuser_client.get("/api/meta/unknown_entity_xyz")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "error"
    assert "not found" in payload["message"].lower()


@pytest.mark.asyncio
async def test_create_role_via_post(superuser_client, record_id_factory):
    """Assert POST /api/entity/{entity} creates a record and returns 201."""
    role_name = f"TestRole-{record_id_factory('role')}"
    payload = {
        "data": {
            "name": role_name,
            "description": "Created by generic entity contract tests",
            "is_active": True,
        },
    }
    resp = await superuser_client.post("/api/entity/role", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["name"] == role_name
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_list_and_detail_created_role(superuser_client, record_id_factory):
    """Assert created roles appear in /api/entity/role/list and /api/entity/role/detail/{id}."""
    role_name = f"ListRole-{record_id_factory('role')}"
    create_resp = await superuser_client.post(
        "/api/entity/role",
        json={
            "data": {"name": role_name, "is_active": True},
        },
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["data"]["id"]

    list_resp = await superuser_client.get(
        f"/api/entity/role/list?filter_field=name&filter_value={role_name}"
    )
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["status"] == "success"
    assert list_payload["total"] == 1
    assert list_payload["data"][0]["name"] == role_name

    detail_resp = await superuser_client.get(f"/api/entity/role/detail/{created_id}")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload["status"] == "success"
    assert detail_payload["data"]["id"] == created_id
    assert detail_payload["data"]["name"] == role_name


@pytest.mark.asyncio
async def test_update_role_via_put(superuser_client, record_id_factory):
    """Assert PUT /api/entity/role/{id} mutates an existing record and returns 200."""
    original_name = f"UpdateRole-{record_id_factory('role')}"
    new_name = f"Updated-{original_name}"

    create_resp = await superuser_client.post(
        "/api/entity/role",
        json={"data": {"name": original_name, "is_active": True}},
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["data"]["id"]

    update_resp = await superuser_client.put(
        f"/api/entity/role/{created_id}",
        json={"data": {"name": new_name}},
    )
    assert update_resp.status_code == 200
    update_payload = update_resp.json()
    assert update_payload["status"] == "success"

    detail_resp = await superuser_client.get(f"/api/entity/role/detail/{created_id}")
    assert detail_resp.json()["data"]["name"] == new_name


@pytest.mark.asyncio
async def test_delete_role(superuser_client, record_id_factory):
    """Assert DELETE /api/entity/role/{id} removes the record."""
    role_name = f"DeleteRole-{record_id_factory('role')}"
    create_resp = await superuser_client.post(
        "/api/entity/role",
        json={"data": {"name": role_name, "is_active": True}},
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["data"]["id"]

    list_before = await superuser_client.get(
        f"/api/entity/role/list?filter_field=name&filter_value={role_name}"
    )
    assert list_before.json()["total"] == 1

    delete_resp = await superuser_client.delete(f"/api/entity/role/{created_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "success"

    list_after = await superuser_client.get(
        f"/api/entity/role/list?filter_field=name&filter_value={role_name}"
    )
    assert list_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_create_rejects_unknown_entity(superuser_client):
    """Assert POST /api/entity/{entity} returns 404 for an unknown entity."""
    resp = await superuser_client.post(
        "/api/entity/unknown_entity_xyz",
        json={"data": {"name": "x"}},
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["status"] == "error"
    assert "not found" in payload["message"].lower()


@pytest.mark.asyncio
async def test_update_returns_404_for_unknown_record(superuser_client, record_id_factory):
    """Assert PUT /api/entity/role/{id} returns 404 when the record does not exist."""
    resp = await superuser_client.put(
        "/api/entity/role/does-not-exist-xyz",
        json={"data": {"name": "ghost"}},
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["status"] == "error"
