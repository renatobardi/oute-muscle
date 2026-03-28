"""Domain value objects — enums used across the incident guardrails platform.

All enums use StrEnum so values serialize to plain strings in JSON/DB.
"""

from enum import StrEnum


class IncidentCategory(StrEnum):
    """The 10 categories of production incidents (maps to Semgrep rule categories)."""

    UNSAFE_REGEX = "unsafe-regex"
    RACE_CONDITION = "race-condition"
    MISSING_ERROR_HANDLING = "missing-error-handling"
    INJECTION = "injection"
    RESOURCE_EXHAUSTION = "resource-exhaustion"
    MISSING_SAFETY_CHECK = "missing-safety-check"
    DEPLOYMENT_ERROR = "deployment-error"
    DATA_CONSISTENCY = "data-consistency"
    UNSAFE_API_USAGE = "unsafe-api-usage"
    CASCADING_FAILURE = "cascading-failure"


class IncidentSeverity(StrEnum):
    """Severity of a production incident or finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(StrEnum):
    """Computed risk level for a scan (Layer 2 output)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlanTier(StrEnum):
    """Subscription tier for a tenant."""

    FREE = "free"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class UserRole(StrEnum):
    """Role of a user within a tenant."""

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class RuleSource(StrEnum):
    """Origin of a Semgrep rule."""

    MANUAL = "manual"
    SYNTHESIZED = "synthesized"


class RuleSeverity(StrEnum):
    """Severity level used in Semgrep rule YAML (maps to Semgrep severity field)."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ScanTriggerSource(StrEnum):
    """What triggered the scan."""

    GITHUB_PUSH = "github_push"
    GITHUB_PR = "github_pr"
    MCP = "mcp"
    REST_API = "rest_api"
    PRE_COMMIT = "pre_commit"


class ScanStatus(StrEnum):
    """Lifecycle status of a scan."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AuditAction(StrEnum):
    """Actions recorded in the immutable audit log."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    HARD_DELETE = "hard_delete"
    APPROVE = "approve"
    DISABLE = "disable"


class SynthesisCandidateStatus(StrEnum):
    """Lifecycle status of an auto-generated rule candidate (Layer 3)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    FAILED = "failed"
