"""Add false positive tracking fields to finding and semgrep_rule tables.

FR-028: False positive reporting with auto-disable at threshold 3.

Revision ID: 003
Revises: 002
Create Date: 2026-03-29
"""

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    """Add false_positive_count and status to finding; false_positive_count and auto_disabled to semgrep_rule."""
    # Finding table
    op.add_column(
        "finding",
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
    )
    op.add_column(
        "finding",
        sa.Column("false_positive_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # SemgrepRule table
    op.add_column(
        "semgrep_rule",
        sa.Column("false_positive_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "semgrep_rule",
        sa.Column("auto_disabled", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove false positive tracking fields."""
    op.drop_column("semgrep_rule", "auto_disabled")
    op.drop_column("semgrep_rule", "false_positive_count")
    op.drop_column("finding", "false_positive_count")
    op.drop_column("finding", "status")
