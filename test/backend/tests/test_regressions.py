"""Regression tests for security, ownership, partial updates, and caching."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


async def register_user(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 201
    return response.json()


async def create_todo(
    client: AsyncClient,
    token: str,
    title: str = "Regression Todo",
    description: str | None = "Important details",
) -> dict:
    payload = {"title": title}
    if description is not None:
        payload["description"] = description

    response = await client.post(
        "/api/v1/todos",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected(client: AsyncClient):
    """Expired JWTs must not authorize protected endpoints."""
    tokens = await register_user(client, "expired-token@example.com")
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    user_id = me_response.json()["id"]

    expired_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=-1),
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [("GET", ""), ("PUT", ""), ("DELETE", "")])
async def test_user_cannot_access_another_users_todo(
    client: AsyncClient,
    method: str,
    path: str,
):
    """User A must not read, update, or delete a todo owned by User B."""
    user_a = await register_user(client, f"owner-boundary-a-{method.lower()}@example.com")
    user_b = await register_user(client, f"owner-boundary-b-{method.lower()}@example.com")
    todo = await create_todo(
        client,
        user_b["access_token"],
        title=f"Private Todo {method}",
    )

    url = f"/api/v1/todos/{todo['id']}{path}"
    headers = {"Authorization": f"Bearer {user_a['access_token']}"}

    if method == "GET":
        response = await client.get(url, headers=headers)
    elif method == "PUT":
        response = await client.put(url, json={"title": "Stolen update"}, headers=headers)
    else:
        response = await client.delete(url, headers=headers)

    assert response.status_code in {403, 404}

    owner_read = await client.get(
        f"/api/v1/todos/{todo['id']}",
        headers={"Authorization": f"Bearer {user_b['access_token']}"},
    )
    assert owner_read.status_code == 200
    assert owner_read.json()["title"] == f"Private Todo {method}"


@pytest.mark.asyncio
async def test_completed_can_be_toggled_from_true_back_to_false(client: AsyncClient):
    """Boolean false is a valid partial update value and must persist."""
    tokens = await register_user(client, "toggle-false@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    todo = await create_todo(client, tokens["access_token"], title="Toggle me")

    mark_done = await client.put(
        f"/api/v1/todos/{todo['id']}",
        json={"completed": True},
        headers=headers,
    )
    assert mark_done.status_code == 200
    assert mark_done.json()["completed"] is True

    mark_active = await client.put(
        f"/api/v1/todos/{todo['id']}",
        json={"completed": False},
        headers=headers,
    )
    assert mark_active.status_code == 200
    assert mark_active.json()["completed"] is False

    persisted = await client.get(f"/api/v1/todos/{todo['id']}", headers=headers)
    assert persisted.status_code == 200
    assert persisted.json()["completed"] is False


@pytest.mark.asyncio
async def test_partial_title_update_keeps_existing_description(client: AsyncClient):
    """Updating only title must not overwrite an existing description with null."""
    tokens = await register_user(client, "partial-update@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    todo = await create_todo(
        client,
        tokens["access_token"],
        title="Original title",
        description="Do not erase me",
    )

    response = await client.put(
        f"/api/v1/todos/{todo['id']}",
        json={"title": "Updated title"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["description"] == "Do not erase me"


@pytest.mark.asyncio
async def test_todo_mutations_invalidate_cached_todo_lists(client: AsyncClient, redis_mock):
    """Create, update, and delete should remove stale todo-list cache entries."""
    tokens = await register_user(client, "cache-invalidation@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    created = await client.post(
        "/api/v1/todos",
        json={"title": "Cache target"},
        headers=headers,
    )
    assert created.status_code == 201
    assert redis_mock.delete.await_count >= 1

    redis_mock.delete.reset_mock()
    updated = await client.put(
        f"/api/v1/todos/{created.json()['id']}",
        json={"title": "Cache target updated"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert redis_mock.delete.await_count >= 1

    redis_mock.delete.reset_mock()
    deleted = await client.delete(
        f"/api/v1/todos/{created.json()['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert redis_mock.delete.await_count >= 1
