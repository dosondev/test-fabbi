# Technical Specification: Todo List Sharing

## 1. Overview & Objective

### Feature Summary

Allow a user to share their todo list with another registered user using one of two permission levels:

- `viewer`: can read the owner's shared todos.
- `editor`: can read and modify the owner's shared todos.

The owner can revoke access at any time. Revocation must take effect immediately for API authorization and cached todo-list responses.

### Problem Statement

Currently todos are private to the owning user. There is no way for a user to collaborate with another user without sharing account credentials or duplicating todo data. This feature adds controlled collaboration while preserving ownership, permission boundaries, and data isolation.

### Current System Assumption

The current system does not have a separate `TodoList` entity. Each todo row belongs directly to one `users.id` through `todos.user_id`.

For this release, "share todo list" means sharing the owner's personal todo collection, identified by `owner_user_id`. A future release may introduce a first-class `todo_lists` table if users need multiple named lists.

### Target Audience / Roles

- `owner`: the user who owns the todo list and grants/revokes access.
- `viewer`: a user with read-only access to another user's shared todo list.
- `editor`: a user with read and edit access to another user's shared todo list.

## 2. User Stories & Acceptance Criteria

### User Story 1: Owner shares todo list as viewer

- **As an** owner
- **I want to** share my todo list with another user as a viewer
- **So that** they can see my todos without changing them

**Acceptance Criteria**:
- [ ] Owner can share with an existing user by email.
- [ ] The recipient can see the owner's shared todo list.
- [ ] The recipient cannot create, update, complete, or delete todos in the shared list.
- [ ] The owner cannot share with themselves.
- [ ] Duplicate share attempts return a clear conflict error.

### User Story 2: Owner shares todo list as editor

- **As an** owner
- **I want to** share my todo list with edit permission
- **So that** another user can help maintain my todos

**Acceptance Criteria**:
- [ ] Owner can grant `editor` permission to an existing user.
- [ ] Editor can read the owner's shared todos.
- [ ] Editor can update title, description, and completed status.
- [ ] Editor can create todos in the owner's list if product accepts collaborative creation in this release.
- [ ] Editor can delete todos only if explicitly allowed by the permission matrix below.
- [ ] Editor cannot share the list with other users.
- [ ] Editor cannot revoke another user's access.

### User Story 3: Owner revokes access

- **As an** owner
- **I want to** revoke shared access anytime
- **So that** the recipient immediately loses access to my todo list

**Acceptance Criteria**:
- [ ] Owner can revoke viewer/editor access.
- [ ] Revoked user immediately receives `403 Forbidden` or `404 Not Found` when accessing the shared list.
- [ ] Redis cache entries affected by the shared relationship are invalidated immediately.
- [ ] Revoked users cannot continue using stale cached data.

### User Story 4: Collaborator lists shared todo lists

- **As a** viewer/editor
- **I want to** see lists shared with me
- **So that** I can choose which todo list to open

**Acceptance Criteria**:
- [ ] User can list all active shares where they are the recipient.
- [ ] Each shared list includes owner email and permission level.
- [ ] Revoked shares are not returned.

## 3. Scope

### In-Scope

- Share current user's personal todo list with another registered user.
- Permission levels: `viewer`, `editor`.
- Owner can list shares they granted.
- Recipient can list todo lists shared with them.
- Owner can update permission from `viewer` to `editor` or from `editor` to `viewer`.
- Owner can revoke access.
- Authorization checks for reading, creating, updating, completing, and deleting todos in shared lists.
- Cache invalidation for owner and recipient views when share is created, updated, or revoked.
- Audit-friendly timestamps for share creation/update/revoke.

### Out-of-Scope

- Public share links.
- Sharing with non-registered emails or invite emails.
- Multiple named todo lists per user.
- Team/workspace roles.
- Commenting, activity feeds, notifications.
- Real-time collaboration or websocket updates.
- Fine-grained permissions per individual todo.
- Transfer of ownership.
- Soft-delete restore UI for revoked shares.

## 4. Database Design

### New Table: `todo_list_shares`

This table represents access granted from an owner to a recipient for the owner's personal todo list.

| Column | Type | Nullable | Description |
|---|---:|---:|---|
| `id` | UUID | No | Primary key. |
| `owner_user_id` | UUID | No | User who owns the todo list. FK to `users.id`. |
| `recipient_user_id` | UUID | No | User receiving access. FK to `users.id`. |
| `permission` | VARCHAR(20) | No | Allowed values: `viewer`, `editor`. |
| `created_at` | TIMESTAMPTZ | No | When share was created. |
| `updated_at` | TIMESTAMPTZ | No | When permission was last changed. |
| `revoked_at` | TIMESTAMPTZ | Yes | Null means active; non-null means revoked. |

### Constraints

- Primary key: `id`.
- Foreign key: `owner_user_id -> users(id)` with `ON DELETE CASCADE`.
- Foreign key: `recipient_user_id -> users(id)` with `ON DELETE CASCADE`.
- Check constraint: `owner_user_id <> recipient_user_id` to prevent self-sharing.
- Check constraint: `permission IN ('viewer', 'editor')`.
- Unique active share per owner/recipient:
  - Recommended PostgreSQL partial unique index:
    - `UNIQUE (owner_user_id, recipient_user_id) WHERE revoked_at IS NULL`
  - This allows historical revoked rows while preventing duplicate active shares.

### Indexes

- `idx_todo_list_shares_owner_active` on `(owner_user_id, revoked_at)` for owner managing granted shares.
- `idx_todo_list_shares_recipient_active` on `(recipient_user_id, revoked_at)` for listing shares received by a user.
- `idx_todo_list_shares_owner_recipient_active` unique partial index on `(owner_user_id, recipient_user_id)` where `revoked_at IS NULL`.

### Cascade Delete Behavior

- If owner user is deleted, their granted shares are deleted.
- If recipient user is deleted, shares granted to that recipient are deleted.
- Todos remain owned by `todos.user_id`; sharing does not duplicate todo rows.

### Optional Future Table: `todo_lists`

Not included in this release. If the product later supports multiple named lists, introduce:

- `todo_lists(id, owner_user_id, name, created_at, updated_at)`
- Change `todos.user_id` to `todos.list_id`, or add `list_id` while migrating existing todos.
- Change shares from `owner_user_id` to `todo_list_id`.

## 5. API Contracts & Endpoints

All endpoints require authentication using Bearer access token.

### Share Management

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/todo-shares` | Share current user's todo list with another user. | Yes |
| `GET` | `/api/v1/todo-shares/outgoing` | List shares granted by current user. | Yes |
| `GET` | `/api/v1/todo-shares/incoming` | List todo lists shared with current user. | Yes |
| `PATCH` | `/api/v1/todo-shares/{share_id}` | Change permission for an active share. | Yes |
| `DELETE` | `/api/v1/todo-shares/{share_id}` | Revoke access. | Yes |

### Shared Todo Access

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/shared-todos/{owner_user_id}` | List todos shared by owner. | Yes |
| `POST` | `/api/v1/shared-todos/{owner_user_id}` | Create todo in owner's list if user is editor. | Yes |
| `GET` | `/api/v1/shared-todos/{owner_user_id}/{todo_id}` | Read one shared todo. | Yes |
| `PUT` | `/api/v1/shared-todos/{owner_user_id}/{todo_id}` | Update shared todo if user is editor. | Yes |
| `DELETE` | `/api/v1/shared-todos/{owner_user_id}/{todo_id}` | Delete shared todo if user is editor and delete is allowed. | Yes |

Alternative API design: reuse existing `/api/v1/todos` with a query parameter like `?owner_user_id=...`. The separate `/shared-todos` namespace is recommended because it keeps ownership and collaboration semantics explicit.

### Request Schemas

#### `POST /api/v1/todo-shares`

```json
{
  "recipient_email": "collaborator@example.com",
  "permission": "viewer"
}
```

Validation:
- `recipient_email`: required, valid email.
- `permission`: required, one of `viewer`, `editor`.

Success response: `201 Created`

```json
{
  "id": "share-uuid",
  "owner_user_id": "owner-uuid",
  "recipient_user_id": "recipient-uuid",
  "recipient_email": "collaborator@example.com",
  "permission": "viewer",
  "created_at": "2026-09-16T10:00:00Z",
  "updated_at": "2026-09-16T10:00:00Z"
}
```

#### `PATCH /api/v1/todo-shares/{share_id}`

```json
{
  "permission": "editor"
}
```

Success response: `200 OK`

#### `GET /api/v1/todo-shares/outgoing`

Success response: `200 OK`

```json
{
  "items": [
    {
      "id": "share-uuid",
      "recipient_user_id": "recipient-uuid",
      "recipient_email": "collaborator@example.com",
      "permission": "editor",
      "created_at": "2026-09-16T10:00:00Z",
      "updated_at": "2026-09-16T10:05:00Z"
    }
  ]
}
```

#### `GET /api/v1/todo-shares/incoming`

Success response: `200 OK`

```json
{
  "items": [
    {
      "share_id": "share-uuid",
      "owner_user_id": "owner-uuid",
      "owner_email": "owner@example.com",
      "permission": "viewer",
      "created_at": "2026-09-16T10:00:00Z"
    }
  ]
}
```

#### `GET /api/v1/shared-todos/{owner_user_id}?page=1&size=20`

Success response: `200 OK`

```json
{
  "items": [
    {
      "id": "todo-uuid",
      "title": "Prepare release notes",
      "description": "Draft before Friday",
      "completed": false,
      "user_id": "owner-uuid",
      "created_at": "2026-09-16T10:00:00Z",
      "updated_at": "2026-09-16T10:00:00Z",
      "user_email": "owner@example.com"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "permission": "viewer"
}
```

### Error Payload Format

Use existing FastAPI error style unless the project standard changes:

```json
{
  "detail": "Error message"
}
```

Recommended status codes:

| Status | When |
|---:|---|
| `400 Bad Request` | Self-sharing, invalid permission, malformed request. |
| `401 Unauthorized` | Missing/invalid/expired token. |
| `403 Forbidden` | Authenticated user lacks permission for this action. |
| `404 Not Found` | Share, user, owner, or todo not found. Prefer `404` where revealing existence would leak private data. |
| `409 Conflict` | Duplicate active share already exists. |
| `422 Unprocessable Entity` | Pydantic validation error. |

## 6. Authorization Matrix

| Action | Owner | Viewer | Editor | Non-shared User |
|---|---:|---:|---:|---:|
| View owner's todo list | Yes | Yes | Yes | No |
| View one todo | Yes | Yes | Yes | No |
| Create todo in owner's list | Yes | No | Yes | No |
| Update title/description | Yes | No | Yes | No |
| Toggle completed | Yes | No | Yes | No |
| Delete todo | Yes | No | Yes, if product accepts editor delete | No |
| Share list with another user | Yes | No | No | No |
| Change recipient permission | Yes | No | No | No |
| Revoke access | Yes | No | No | No |
| View share recipients | Yes | No | No | No |

Recommendation: allow editor delete only if product explicitly wants full edit permission. If delete feels too destructive, split permission later into `editor` and `manager`, but keep this release simple.

## 7. Business Logic & Edge Cases

### Self-Sharing Prevention

If `recipient_user_id == current_user.id`, return `400 Bad Request`.

Reason: owner already has full access; self-share creates confusing duplicate permissions.

### Duplicate Invites

If an active share already exists for `(owner_user_id, recipient_user_id)`, return `409 Conflict`.

Optional behavior: allow `POST` to update permission if the existing share is active. For this release, prefer explicit `PATCH` to avoid accidental permission changes.

### Revoked Access

When `revoked_at` is non-null, the share is inactive.

- Incoming share list must not show it.
- Shared todo endpoints must deny access immediately.
- Cached shared-list responses must be invalidated immediately.
- If the owner shares again with the same recipient, create a new active share row or reactivate old row. Recommended: create a new row for better audit history.

### Concurrent Updates

Possible race cases:
- Owner revokes access while editor submits an update.
- Owner downgrades editor to viewer while editor submits update.
- Two editors update the same todo at the same time.

Rules:
- Authorization must be checked inside the request transaction as close as possible to the write.
- If permission is revoked/downgraded before the write commits, return `403 Forbidden`.
- Last write wins for todo field updates in this release.
- Future improvement: optimistic locking using `updated_at` or a `version` column.

### User Not Found

If `recipient_email` does not match an existing user, return `404 Not Found` with:

```json
{
  "detail": "Recipient user not found"
}
```

No email invitation flow in this release.

### Todo Not Found Or Not Shared

For shared todo detail/update/delete:
- If todo ID does not belong to `owner_user_id`, return `404 Not Found`.
- If current user has no active share, return `404 Not Found` or `403 Forbidden`.
- Recommendation: return `404 Not Found` to avoid leaking whether the owner/todo exists.

### Cache Invalidation Immediately After Revoke

Revoking access must invalidate:
- Owner's outgoing share cache.
- Recipient's incoming share cache.
- Recipient's cached shared todo list for that owner.
- Any cached todo detail for that shared owner/recipient pair.

This invalidation happens in the same service flow as the revoke operation after DB commit succeeds, or through a transaction hook/outbox if available.

## 8. Caching & Invalidation Strategy

### Cache Key Design

Private owner list:

```text
todos:list:{owner_user_id}:page:{page}:size:{size}
```

Incoming shares for recipient:

```text
todo-shares:incoming:{recipient_user_id}
```

Outgoing shares for owner:

```text
todo-shares:outgoing:{owner_user_id}
```

Shared todo list viewed by recipient:

```text
shared-todos:list:{owner_user_id}:recipient:{recipient_user_id}:page:{page}:size:{size}
```

Shared todo detail:

```text
shared-todos:detail:{owner_user_id}:recipient:{recipient_user_id}:todo:{todo_id}
```

### Invalidation Events

| Event | Cache to Invalidate |
|---|---|
| Owner creates/updates/deletes todo | Owner private list; all active recipients' shared todo list caches for that owner. |
| Editor creates/updates/deletes todo | Owner private list; all active recipients' shared todo list caches for that owner. |
| Owner creates share | Owner outgoing shares; recipient incoming shares; recipient shared todo list. |
| Owner changes permission | Owner outgoing shares; recipient incoming shares; recipient shared todo list/detail. |
| Owner revokes share | Owner outgoing shares; recipient incoming shares; recipient shared todo list/detail immediately. |
| Recipient user deleted | Owner outgoing shares; related shared list caches. |
| Owner user deleted | Recipient incoming shares; related shared list caches. |

### Cache Safety Rules

- Never use a shared cache key that omits `recipient_user_id` for shared views.
- Do not cache authorization failures for long TTLs.
- Always check DB permission before serving shared todo data if cache contents do not encode permission safely.
- Keep TTL short, e.g. 5 minutes, but do not rely on TTL for revoke safety. Revoke must invalidate immediately.

## 9. Test Strategy

### Backend Tests

- Owner can create share with viewer permission.
- Owner can create share with editor permission.
- Self-sharing returns `400`.
- Duplicate active share returns `409`.
- Unknown recipient email returns `404`.
- Viewer can read shared todos.
- Viewer cannot create/update/delete shared todos.
- Editor can read and update shared todos.
- Revoked recipient can no longer read shared todos.
- Revoke invalidates recipient shared list cache.
- User without share cannot access owner's shared todos.

### E2E Tests

- Owner shares todo list with viewer; viewer logs in and sees owner todos read-only.
- Owner shares todo list with editor; editor updates a todo; owner sees update.
- Owner revokes editor; editor refreshes and immediately loses access.

## 10. Rollout Notes

- Add DB migration for `todo_list_shares` first.
- Deploy backend authorization changes before exposing frontend sharing UI.
- Monitor 403/404 rates on shared todo endpoints after launch.
- Log share create/update/revoke events for audit and debugging.
