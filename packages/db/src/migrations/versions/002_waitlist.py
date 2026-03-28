"""Waitlist table for beta access requests.

Revision ID: 002
Revises: 001
Create Date: 2026-03-28
"""

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Create waitlist table."""
    op.create_table(
        "waitlist",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("source", sa.String(64), nullable=True, server_default="landing"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_waitlist_email"),
    )
    op.create_index("ix_waitlist_created_at", "waitlist", ["created_at"])


def downgrade() -> None:
    """Drop waitlist table."""
    op.drop_index("ix_waitlist_created_at", table_name="waitlist")
    op.drop_table("waitlist")
