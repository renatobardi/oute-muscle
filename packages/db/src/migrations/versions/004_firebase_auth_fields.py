"""Add Firebase Auth fields to user table.

Spec 237: firebase_uid links to shared Firebase project oute-488706.
tenant_id changed to nullable for JIT-provisioned users (pending approval).

Revision ID: 004
Revises: 003
Create Date: 2026-03-29
"""

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    """Add firebase_uid, display_name, email_verified, last_login to user table."""
    op.add_column(
        "user",
        sa.Column("firebase_uid", sa.String(128), nullable=True),
    )
    op.create_unique_constraint("uq_user_firebase_uid", "user", ["firebase_uid"])
    op.create_index("ix_user_firebase_uid", "user", ["firebase_uid"])

    op.add_column(
        "user",
        sa.Column("display_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "user",
        sa.Column("last_login", sa.DateTime(), nullable=True),
    )

    # Make tenant_id nullable for JIT-provisioned users (pending approval)
    op.alter_column("user", "tenant_id", nullable=True)


def downgrade() -> None:
    """Remove Firebase Auth fields from user table."""
    op.alter_column("user", "tenant_id", nullable=False)
    op.drop_column("user", "last_login")
    op.drop_column("user", "email_verified")
    op.drop_column("user", "display_name")
    op.drop_index("ix_user_firebase_uid", table_name="user")
    op.drop_constraint("uq_user_firebase_uid", "user")
    op.drop_column("user", "firebase_uid")
