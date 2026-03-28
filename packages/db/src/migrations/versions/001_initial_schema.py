"""Initial schema migration.

Creates all tables, enums, indexes, RLS policies, and constraints.
Constitution VI: Row-Level Security policies enforce tenant isolation.

Revision ID: 001
Revises:
Create Date: 2026-03-28
"""

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


def upgrade() -> None:
    """Apply migration."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create enum types
    incident_category = postgresql.ENUM(
        "unsafe-regex",
        "race-condition",
        "missing-error-handling",
        "injection",
        "resource-exhaustion",
        "missing-safety-check",
        "deployment-error",
        "data-consistency",
        "unsafe-api-usage",
        "cascading-failure",
        name="incident_category",
    )
    incident_category.create(op.get_bind())

    severity_enum = postgresql.ENUM(
        "critical", "high", "medium", "low", name="severity"
    )
    severity_enum.create(op.get_bind())

    plan_tier_enum = postgresql.ENUM(
        "free", "team", "enterprise", name="plan_tier"
    )
    plan_tier_enum.create(op.get_bind())

    user_role_enum = postgresql.ENUM(
        "viewer", "editor", "admin", name="user_role"
    )
    user_role_enum.create(op.get_bind())

    rule_source_enum = postgresql.ENUM(
        "manual", "synthesized", name="rule_source"
    )
    rule_source_enum.create(op.get_bind())

    rule_severity_enum = postgresql.ENUM(
        "error", "warning", "info", name="rule_severity"
    )
    rule_severity_enum.create(op.get_bind())

    scan_trigger_source_enum = postgresql.ENUM(
        "github_push",
        "github_pr",
        "mcp",
        "rest_api",
        "pre_commit",
        name="scan_trigger_source",
    )
    scan_trigger_source_enum.create(op.get_bind())

    scan_status_enum = postgresql.ENUM(
        "running", "completed", "failed", "timeout", name="scan_status"
    )
    scan_status_enum.create(op.get_bind())

    audit_action_enum = postgresql.ENUM(
        "create",
        "update",
        "delete",
        "soft_delete",
        "hard_delete",
        "approve",
        "disable",
        name="audit_action",
    )
    audit_action_enum.create(op.get_bind())

    synthesis_status_enum = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        "archived",
        "failed",
        name="synthesis_status",
    )
    synthesis_status_enum.create(op.get_bind())

    # Create tables
    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan_tier", sa.String(50), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenant_slug", "tenant", ["slug"])

    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_tenant_id", "user", ["tenant_id"])
    op.create_index("ix_user_email", "user", ["email"])

    op.create_table(
        "incident",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("date", sa.Date, nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("organization", sa.String(255), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("failure_mode", sa.Text, nullable=True),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("affected_languages", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("anti_pattern", sa.Text, nullable=False),
        sa.Column("code_example", sa.Text, nullable=True),
        sa.Column("remediation", sa.Text, nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String(100)), nullable=False, server_default="{}"),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("static_rule_possible", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("semgrep_rule_id", sa.String(50), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("version >= 1", name="check_incident_version_positive"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index("ix_incident_tenant_id", "incident", ["tenant_id"])
    op.create_index("ix_incident_category", "incident", ["category"])
    op.create_index("ix_incident_severity", "incident", ["severity"])
    op.create_index("ix_incident_source_url", "incident", ["source_url"])
    op.create_index("ix_incident_semgrep_rule_id", "incident", ["semgrep_rule_id"])
    op.create_index("ix_incident_deleted_at", "incident", ["deleted_at"])
    # HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX ix_incident_embedding ON incident USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "semgrep_rule",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("sequence_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("yaml_content", sa.Text, nullable=False),
        sa.Column("test_file_content", sa.Text, nullable=False),
        sa.Column("languages", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("remediation", sa.Text, nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("sequence_number >= 1", name="check_rule_sequence_positive"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incident.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_semgrep_rule_tenant_id", "semgrep_rule", ["tenant_id"])
    op.create_index("ix_semgrep_rule_incident_id", "semgrep_rule", ["incident_id"])
    op.create_index("ix_semgrep_rule_category", "semgrep_rule", ["category"])

    op.create_table(
        "scan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_source", sa.String(50), nullable=False),
        sa.Column("repository", sa.String(1024), nullable=False),
        sa.Column("pr_number", sa.Integer, nullable=True),
        sa.Column("commit_sha", sa.String(40), nullable=False),
        sa.Column("diff_lines", sa.Integer, nullable=False, server_default="0"),
        sa.Column("diff_truncated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("llm_model_used", sa.String(50), nullable=True),
        sa.Column("layer1_findings_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("layer2_advisories_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="check_scan_risk_score_range",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_tenant_id", "scan", ["tenant_id"])
    op.create_index("ix_scan_commit_sha", "scan", ["commit_sha"])

    op.create_table(
        "finding",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("start_line", sa.Integer, nullable=False),
        sa.Column("end_line", sa.Integer, nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("remediation", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scan.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incident.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_scan_id", "finding", ["scan_id"])
    op.create_index("ix_finding_tenant_id", "finding", ["tenant_id"])
    op.create_index("ix_finding_rule_id", "finding", ["rule_id"])
    op.create_index("ix_finding_incident_id", "finding", ["incident_id"])

    op.create_table(
        "advisory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("remediation_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scan.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incident.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_advisory_scan_id", "advisory", ["scan_id"])
    op.create_index("ix_advisory_tenant_id", "advisory", ["tenant_id"])
    op.create_index("ix_advisory_incident_id", "advisory", ["incident_id"])

    op.create_table(
        "audit_log_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("changes", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entry_tenant_id", "audit_log_entry", ["tenant_id"])
    op.create_index("ix_audit_log_entry_action", "audit_log_entry", ["action"])
    op.create_index("ix_audit_log_entry_entity_type", "audit_log_entry", ["entity_type"])
    op.create_index("ix_audit_log_entry_entity_id", "audit_log_entry", ["entity_id"])

    op.create_table(
        "synthesis_candidate",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposed_rule_id", sa.String(50), nullable=False),
        sa.Column("yaml_content", sa.Text, nullable=False),
        sa.Column("test_file_content", sa.Text, nullable=False),
        sa.Column("languages", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incident.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_synthesis_candidate_tenant_id", "synthesis_candidate", ["tenant_id"])
    op.create_index(
        "ix_synthesis_candidate_incident_id", "synthesis_candidate", ["incident_id"]
    )
    op.create_index("ix_synthesis_candidate_status", "synthesis_candidate", ["status"])

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Enable RLS on tables
    op.execute("ALTER TABLE incident ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE semgrep_rule ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE scan ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE finding ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE advisory ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log_entry ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE synthesis_candidate ENABLE ROW LEVEL SECURITY")

    # RLS policies (tenant isolation)
    op.execute(
        """
        CREATE POLICY incident_rls ON incident USING (
            (tenant_id = current_setting('app.tenant_id')::uuid OR tenant_id IS NULL)
            AND deleted_at IS NULL
        )
    """
    )
    op.execute(
        """
        CREATE POLICY semgrep_rule_rls ON semgrep_rule USING (
            (tenant_id = current_setting('app.tenant_id')::uuid OR tenant_id IS NULL)
        )
    """
    )
    op.execute(
        """
        CREATE POLICY scan_rls ON scan USING (
            tenant_id = current_setting('app.tenant_id')::uuid
        )
    """
    )
    op.execute(
        """
        CREATE POLICY finding_rls ON finding USING (
            tenant_id = current_setting('app.tenant_id')::uuid
        )
    """
    )
    op.execute(
        """
        CREATE POLICY advisory_rls ON advisory USING (
            tenant_id = current_setting('app.tenant_id')::uuid
        )
    """
    )
    op.execute(
        """
        CREATE POLICY audit_log_entry_rls ON audit_log_entry USING (
            tenant_id = current_setting('app.tenant_id')::uuid
        )
    """
    )
    op.execute(
        """
        CREATE POLICY synthesis_candidate_rls ON synthesis_candidate USING (
            tenant_id = current_setting('app.tenant_id')::uuid
        )
    """
    )


def downgrade() -> None:
    """Revert migration."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS incident_rls ON incident")
    op.execute("DROP POLICY IF EXISTS semgrep_rule_rls ON semgrep_rule")
    op.execute("DROP POLICY IF EXISTS scan_rls ON scan")
    op.execute("DROP POLICY IF EXISTS finding_rls ON finding")
    op.execute("DROP POLICY IF EXISTS advisory_rls ON advisory")
    op.execute("DROP POLICY IF EXISTS audit_log_entry_rls ON audit_log_entry")
    op.execute("DROP POLICY IF EXISTS synthesis_candidate_rls ON synthesis_candidate")

    # Drop tables
    op.drop_table("synthesis_candidate")
    op.drop_table("audit_log_entry")
    op.drop_table("advisory")
    op.drop_table("finding")
    op.drop_table("scan")
    op.drop_table("semgrep_rule")
    op.drop_table("incident")
    op.drop_table("user")
    op.drop_table("tenant")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS incident_category")
    op.execute("DROP TYPE IF EXISTS severity")
    op.execute("DROP TYPE IF EXISTS plan_tier")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS rule_source")
    op.execute("DROP TYPE IF EXISTS rule_severity")
    op.execute("DROP TYPE IF EXISTS scan_trigger_source")
    op.execute("DROP TYPE IF EXISTS scan_status")
    op.execute("DROP TYPE IF EXISTS audit_action")
    op.execute("DROP TYPE IF EXISTS synthesis_status")
