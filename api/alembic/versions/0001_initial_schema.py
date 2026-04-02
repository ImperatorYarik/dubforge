"""Initial schema: projects and videos tables

Revision ID: 0001
Revises:
Create Date: 2026-04-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_projects_project_id", "projects", ["project_id"], unique=True)

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("video_id", sa.String(36), nullable=False),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.project_id"),
            nullable=False,
        ),
        sa.Column("video_url", sa.Text, nullable=False),
        sa.Column("transcription", sa.Text, nullable=True),
        sa.Column("transcript_segments", JSONB, nullable=True),
        sa.Column("transcript_url", sa.Text, nullable=True),
        sa.Column("dubbed_url", sa.Text, nullable=True),
        sa.Column("dubbed_versions", JSONB, nullable=True),
        sa.Column("vocals_url", sa.Text, nullable=True),
        sa.Column("no_vocals_url", sa.Text, nullable=True),
        sa.Column("detected_language", sa.String(20), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_videos_video_id", "videos", ["video_id"], unique=True)
    op.create_index("ix_videos_project_id", "videos", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_videos_project_id", table_name="videos")
    op.drop_index("ix_videos_video_id", table_name="videos")
    op.drop_table("videos")
    op.drop_index("ix_projects_project_id", table_name="projects")
    op.drop_table("projects")
