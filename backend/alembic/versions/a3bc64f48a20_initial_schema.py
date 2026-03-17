"""initial schema

Revision ID: a3bc64f48a20
Revises:
Create Date: 2026-03-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a3bc64f48a20"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("picture", sa.String(length=1024), nullable=True),
        sa.Column("google_access_token", sa.Text(), nullable=True),
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "presentations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("youtube_url", sa.String(length=2048), nullable=False),
        sa.Column("video_id", sa.String(length=11), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "done", "failed", name="presentationstatus"),
            nullable=False,
        ),
        sa.Column("pptx_path", sa.String(length=1024), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_presentations_user_id"), "presentations", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_presentations_user_id"), table_name="presentations")
    op.drop_table("presentations")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS presentationstatus")
