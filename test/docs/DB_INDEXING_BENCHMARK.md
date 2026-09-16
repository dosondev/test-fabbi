# Database Indexing Benchmark: Todos

## 1. Objective

This document covers Task 3C: database performance and indexing strategy for core Todo queries.

The goal is to optimize real query patterns used by the backend, not to add indexes broadly.

## 2. Core Query Patterns

The current backend Todo service uses these important access patterns:

1. List todos for the current user, ordered by newest first:

```sql
SELECT id, title, completed, created_at
FROM todos
WHERE user_id = :user_id
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET :offset;
```

2. Count todos for the current user:

```sql
SELECT count(*)
FROM todos
WHERE user_id = :user_id;
```

3. Filter todos by user and completed status, ordered by newest first:

```sql
SELECT id, title, completed, created_at
FROM todos
WHERE user_id = :user_id
  AND completed = true
ORDER BY created_at DESC, id DESC
LIMIT :limit OFFSET :offset;
```

## 3. Dataset And Test Environment

Benchmark was run against the Docker PostgreSQL database.

- Users: 100
- Todos: 1,000
- Target user: `a76f4b5e-36ab-4249-b31d-2730bd3396c0`
- Target user todo count: 20

Because the dataset is small, timings are sub-millisecond and can fluctuate. The most important signal is the query plan change from `Seq Scan` to index-assisted scans. On a larger dataset, avoiding full-table scans becomes much more important.

## 4. Before Indexes

Existing indexes before this task:

```text
todos_pkey ON todos(id)
```

There was no index on `todos.user_id`, `todos.completed`, or `todos.created_at`.

### Before Query Plans Summary

| Query | Plan | Execution Time | Notes |
|---|---|---:|---|
| List todos by user ordered by `created_at DESC, id DESC` | `Seq Scan` + sort | 0.275 ms | Scanned all 1,000 rows; removed 980 by filter. |
| Count todos by user | `Seq Scan` | 0.122 ms | Scanned all 1,000 rows; removed 980 by filter. |
| Filter by user + completed ordered by `created_at DESC, id DESC` | `Seq Scan` + sort | 0.290 ms | Scanned all 1,000 rows; removed 989 by filter. |

Representative Before plan:

```text
Seq Scan on todos
  Filter: (user_id = 'a76f4b5e-36ab-4249-b31d-2730bd3396c0'::uuid)
  Rows Removed by Filter: 980
```

## 5. Index Strategy

Added two indexes via Alembic migration:

```sql
CREATE INDEX IF NOT EXISTS ix_todos_user_created_id
ON todos (user_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS ix_todos_user_completed_created_id
ON todos (user_id, completed, created_at DESC, id DESC);
```

Migration file:

```text
backend/alembic/versions/20260916_add_todo_indexes.py
```

### Why These Indexes

#### `ix_todos_user_created_id`

Supports the default Todo list query:

```sql
WHERE user_id = :user_id
ORDER BY created_at DESC, id DESC
```

`user_id` is first because every Todo list query is scoped to the current user. `created_at DESC, id DESC` matches the sort order and gives stable pagination when multiple rows have the same timestamp.

#### `ix_todos_user_completed_created_id`

Supports status-filtered Todo queries:

```sql
WHERE user_id = :user_id
  AND completed = :completed
ORDER BY created_at DESC, id DESC
```

`completed` is placed after `user_id` because it is only useful inside one user's Todo list. The trailing sort columns preserve newest-first ordering for filtered results.

## 6. After Indexes

Migration applied successfully:

```text
Running upgrade a0790c76a129 -> 20260916_add_todo_indexes
```

Indexes confirmed in Postgres:

```text
ix_todos_user_created_id
ix_todos_user_completed_created_id
todos_pkey
```

After migration, `ANALYZE todos;` was run before measuring.

### After Query Plans Summary

| Query | Plan | Before | After | Improvement | Notes |
|---|---|---:|---:|---:|---|
| List todos by user ordered by `created_at DESC, id DESC` | `Bitmap Index Scan` + heap scan + sort | 0.275 ms | 0.193 ms | ~30% faster | Planner used index-assisted scan. Dataset is small, so sort remains cheap. |
| Count todos by user | `Bitmap Index Scan` + heap scan | 0.122 ms | 0.072 ms | ~41% faster | Avoids full table scan. |
| Filter by user + completed ordered by `created_at DESC, id DESC` | `Bitmap Index Scan` + heap scan + sort | 0.290 ms | 0.103 ms | ~64% faster | Uses composite `(user_id, completed, created_at, id)` index. |

Representative After plan:

```text
Bitmap Index Scan on ix_todos_user_completed_created_id
  Index Cond: ((user_id = 'a76f4b5e-36ab-4249-b31d-2730bd3396c0'::uuid) AND (completed = true))
```

## 7. Notes On Small Dataset Results

The current seeded database has only 1,000 todos. At this size, PostgreSQL may choose a bitmap scan and still sort the small result set because that is cheap.

The important improvement is that PostgreSQL no longer needs to scan every row for user-scoped queries. With the README's larger dataset target, for example 1,000,000 todos, this difference should become much larger.

For a production-scale benchmark, run:

```bash
docker compose exec -e SEED_USERS=10000 -e SEED_TODOS=1000000 backend python -m app.db.seed
```

Then repeat the same `EXPLAIN (ANALYZE, BUFFERS)` queries.

## 8. Tradeoffs

### Write Latency

Every insert/update/delete on `todos` now also updates two additional indexes.

Impact:
- Creating todos is slightly slower.
- Updating `completed`, `created_at`, or `user_id` has extra index maintenance cost.
- Deleting todos removes entries from the indexes.

This is acceptable because todo reads/lists are expected to happen more often than writes.

### Storage Overhead

Each index takes disk space. Two composite indexes cost more storage than a single-column index.

This is acceptable because the indexes match important user-facing query patterns. We should not add additional indexes unless new query patterns justify them.

### Migration Safety On Large Tables

The migration currently uses normal `CREATE INDEX`. On very large production tables, this can lock writes while the index is being built.

Production-safe recommendation:
- Use `CREATE INDEX CONCURRENTLY` for large tables.
- Run outside a normal transaction using Alembic autocommit mode.
- Deploy during a low-traffic window.
- Monitor lock wait time, disk usage, and replication lag.

For this assessment/dev environment, normal `CREATE INDEX` is acceptable and simpler.

### Why Not Add Indexes Broadly

Indexes were added only for observed query patterns:
- list by `user_id` ordered by `created_at`
- count by `user_id`
- filter by `user_id + completed`

No indexes were added for `title`, `description`, or unrelated columns because the current backend does not query by them.

## 9. Commands Used

Before:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, completed, created_at
FROM todos
WHERE user_id = 'a76f4b5e-36ab-4249-b31d-2730bd3396c0'
ORDER BY created_at DESC, id DESC
LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM todos
WHERE user_id = 'a76f4b5e-36ab-4249-b31d-2730bd3396c0';

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, completed, created_at
FROM todos
WHERE user_id = 'a76f4b5e-36ab-4249-b31d-2730bd3396c0'
  AND completed = true
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Migration:

```bash
docker compose run --rm -v "${PWD}\\backend:/app" backend alembic upgrade head
```

After:

```sql
ANALYZE todos;
-- Repeat EXPLAIN ANALYZE queries above.
```
