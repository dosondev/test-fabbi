"""add todo query performance indexes

Revision ID: 20260916_add_todo_indexes
Revises: a0790c76a129
Create Date: 2026-09-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260916_add_todo_indexes"
down_revision: Union[str, None] = "a0790c76a129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_todos_user_created_id "
        "ON todos (user_id, created_at DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_todos_user_completed_created_id "
        "ON todos (user_id, completed, created_at DESC, id DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_todos_user_completed_created_id")
    op.execute("DROP INDEX IF EXISTS ix_todos_user_created_id")
