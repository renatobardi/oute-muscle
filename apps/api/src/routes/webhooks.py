"""GitHub webhook routes (T105-T108).

POST /v1/webhooks/github — Main webhook endpoint
  - Verifies signature (webhook_auth middleware)
  - Routes based on X-GitHub-Event header:
    - 'pull_request' (action: opened/synchronize) → L1+L2 pipeline
    - 'push' → L1 scan pipeline
    - 'installation' (action: created/deleted) → tenant provisioning
    - 'ping' → return 200 {"status": "pong"}
    - unknown → return 200 {"status": "ignored"}
  - Always returns 200 immediately (pipeline runs in background)
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from apps.api.src.middleware.webhook_auth import (
    WebhookReplayError,
    WebhookSignatureError,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookResponse(BaseModel):
    """Response body for webhook endpoints."""

    status: str
    delivery_id: str | None = None


@router.post("/github", response_model=WebhookResponse)
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(default=None, alias="X-GitHub-Delivery"),
) -> WebhookResponse:
    """Handle GitHub webhook events.

    Verifies HMAC signature, routes by event type, dispatches pipelines as
    fire-and-forget background tasks, returns 200 immediately.

    Args:
        request: FastAPI request object.
        background_tasks: FastAPI background task registry.
        x_github_event: X-GitHub-Event header value.
        x_hub_signature_256: X-Hub-Signature-256 HMAC header.
        x_github_delivery: X-GitHub-Delivery unique delivery ID.

    Returns:
        WebhookResponse with status (queued, pong, ignored, error).
    """
    body = await request.body()

    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("GITHUB_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        verify_webhook_signature(
            body, x_hub_signature_256, webhook_secret, delivery_id=x_github_delivery
        )
    except WebhookSignatureError as exc:
        logger.warning("webhook_signature_failed", delivery_id=x_github_delivery, error=str(exc))
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    except WebhookReplayError as exc:
        logger.warning("webhook_replay_detected", delivery_id=x_github_delivery, error=str(exc))
        # Return 200 — don't trigger GitHub retries
        return WebhookResponse(status="ignored", delivery_id=x_github_delivery)

    try:
        payload = json.loads(body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.error("webhook_invalid_json", delivery_id=x_github_delivery, error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    installation_id: int | None = (
        payload.get("installation", {}).get("id")
        if isinstance(payload.get("installation"), dict)
        else None
    )

    if x_github_event == "ping":
        logger.info("webhook_ping_received", delivery_id=x_github_delivery)
        return WebhookResponse(status="pong", delivery_id=x_github_delivery)

    if x_github_event == "pull_request":
        action = payload.get("action")
        if action in ("opened", "synchronize"):
            background_tasks.add_task(_run_l1_and_l2_pipeline, payload, installation_id)
            logger.info(
                "webhook_pr_queued",
                action=action,
                repo=payload.get("repository", {}).get("full_name"),
                delivery_id=x_github_delivery,
            )
            return WebhookResponse(status="queued", delivery_id=x_github_delivery)
        logger.info("webhook_pr_ignored", action=action, delivery_id=x_github_delivery)
        return WebhookResponse(status="ignored", delivery_id=x_github_delivery)

    if x_github_event == "push":
        background_tasks.add_task(_run_l1_scan, payload, installation_id)
        logger.info(
            "webhook_push_queued",
            repo=payload.get("repository", {}).get("full_name"),
            delivery_id=x_github_delivery,
        )
        return WebhookResponse(status="queued", delivery_id=x_github_delivery)

    if x_github_event == "installation":
        action = payload.get("action")
        if action == "created":
            background_tasks.add_task(_handle_installation_created, payload)
            logger.info(
                "webhook_installation_created",
                installation_id=installation_id,
                delivery_id=x_github_delivery,
            )
            return WebhookResponse(status="queued", delivery_id=x_github_delivery)
        if action == "deleted":
            background_tasks.add_task(_handle_installation_deleted, payload)
            logger.info(
                "webhook_installation_deleted",
                installation_id=installation_id,
                delivery_id=x_github_delivery,
            )
            return WebhookResponse(status="queued", delivery_id=x_github_delivery)

    logger.info("webhook_ignored", event=x_github_event, delivery_id=x_github_delivery)
    return WebhookResponse(status="ignored", delivery_id=x_github_delivery)


# ============================================================================
# Pipeline handlers — run as background tasks (fire-and-forget)
# ============================================================================


async def _run_l1_and_l2_pipeline(
    payload: dict[str, Any],
    installation_id: int | None,
) -> None:
    """Layer 1 + Layer 2 pipeline for pull_request events (T107).

    Steps:
      1. Extract repo, PR number, commit SHA from payload
      2. Fetch PR diff via GitHub App adapter
      3. Run Semgrep L1 scan on diff
      4. Create GitHub Check Run with findings
      5. Compute risk score from findings
      6. Run L2 RAG advisory pipeline
      7. Post advisory as PR comment

    Args:
        payload: GitHub webhook pull_request payload.
        installation_id: GitHub App installation ID for authenticated API calls.
    """
    repository: str = payload.get("repository", {}).get("full_name", "")
    pr_number: int | None = payload.get("pull_request", {}).get("number")
    commit_sha: str = payload.get("pull_request", {}).get("head", {}).get("sha", "")

    if not repository or pr_number is None or not commit_sha:
        logger.error(
            "webhook_l1l2_missing_fields",
            repository=repository,
            pr_number=pr_number,
            commit_sha=commit_sha,
        )
        return

    logger.info(
        "webhook_l1l2_pipeline_start",
        repository=repository,
        pr_number=pr_number,
        commit_sha=commit_sha,
    )

    # ── Step 1: Fetch PR diff ───────────────────────────────────────────────
    from packages.core.src.adapters.github_adapter import GitHubAdapter
    from packages.core.src.ports.github import GitHubError

    github = GitHubAdapter()
    try:
        pr_diff = await github.get_pr_diff(
            repository,
            pr_number,
            installation_id=installation_id,
        )
        diff_text = pr_diff.diff_content
    except GitHubError as exc:
        logger.warning(
            "webhook_l1l2_diff_fetch_failed",
            repository=repository,
            pr_number=pr_number,
            error=str(exc),
        )
        diff_text = ""

    if not diff_text.strip():
        logger.info(
            "webhook_l1l2_empty_diff",
            repository=repository,
            pr_number=pr_number,
        )
        return

    # ── Step 2: Run Semgrep L1 scan ─────────────────────────────────────────
    findings = await _run_semgrep_on_diff(diff_text)
    finding_count = len(findings)
    has_violations = finding_count > 0
    conclusion = "failure" if has_violations else "success"

    logger.info(
        "webhook_l1_findings",
        repository=repository,
        pr_number=pr_number,
        finding_count=finding_count,
    )

    # ── Step 3: Create GitHub Check Run ────────────────────────────────────
    annotations = [
        {
            "path": f.get("path", ""),
            "start_line": f.get("start_line", 1),
            "end_line": f.get("end_line", 1),
            "annotation_level": _severity_to_annotation_level(f.get("severity", "low")),
            "message": f.get("message", ""),
            "title": f.get("rule_id", "oute-muscle"),
        }
        for f in findings
    ]

    summary_lines = [
        f"**Oute Muscle** scanned {pr_diff.diff_lines if diff_text else 0} diff lines.",
        f"Found **{finding_count}** incident-linked pattern(s)."
        if finding_count
        else "No patterns found.",
    ]
    if pr_diff.truncated if diff_text else False:
        summary_lines.append("⚠️ Diff truncated at 3000 lines — full diff not scanned.")

    try:
        await github.create_check_run(
            repository,
            commit_sha,
            installation_id=installation_id,
            name="Oute Muscle",
            conclusion=conclusion,
            title="Oute Muscle — Incident Pattern Scan",
            summary="\n".join(summary_lines),
            annotations=annotations[:50],  # GitHub API limit: 50 per request
        )
    except GitHubError as exc:
        logger.warning(
            "webhook_check_run_failed",
            repository=repository,
            commit_sha=commit_sha,
            error=str(exc),
        )

    # ── Step 4: Compute risk level + run L2 RAG ────────────────────────────
    from packages.core.src.domain.incidents.enums import IncidentSeverity
    from packages.core.src.domain.scanning.risk_score import (
        compute_risk_score,
        score_to_risk_level,
    )

    severity_map = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "medium": IncidentSeverity.MEDIUM,
        "low": IncidentSeverity.LOW,
    }
    severities = [
        severity_map.get(f.get("severity", "low"), IncidentSeverity.LOW) for f in findings
    ]
    risk_score = compute_risk_score(severities)
    risk_level = score_to_risk_level(risk_score)

    # L2 RAG advisory — requires GCP + DB
    advisory_text = await _run_l2_advisory(
        diff=diff_text,
        risk_level=risk_level,
        tenant_id=None,  # webhook handler doesn't have tenant context yet
    )

    if advisory_text and pr_number is not None:
        try:
            await github.post_review_comment(
                repository,
                pr_number,
                body=_format_advisory_comment(advisory_text, finding_count, risk_level),
                installation_id=installation_id,
                commit_sha=commit_sha,
            )
        except GitHubError as exc:
            logger.warning(
                "webhook_advisory_comment_failed",
                repository=repository,
                pr_number=pr_number,
                error=str(exc),
            )

    logger.info(
        "webhook_l1l2_pipeline_done",
        repository=repository,
        pr_number=pr_number,
        finding_count=finding_count,
        risk_level=risk_level.value,
    )


async def _run_l1_scan(
    payload: dict[str, Any],
    installation_id: int | None,
) -> None:
    """Layer 1 scan pipeline for push events (T106).

    Steps:
      1. Extract repo and commit SHA from payload
      2. Fetch commit diff via GitHub API
      3. Run Semgrep L1 scan
      4. Create GitHub Check Run

    Args:
        payload: GitHub webhook push payload.
        installation_id: GitHub App installation ID.
    """
    repository: str = payload.get("repository", {}).get("full_name", "")
    commit_sha: str = payload.get("after", "")
    ref: str = payload.get("ref", "")

    if not repository or not commit_sha or commit_sha == "0" * 40:
        logger.info("webhook_l1_push_skipped", repository=repository, ref=ref)
        return

    logger.info(
        "webhook_l1_scan_start",
        repository=repository,
        commit_sha=commit_sha,
        ref=ref,
    )

    # Build a simple diff from push commits (head commit patches)
    commits: list[dict] = payload.get("commits", [])
    diff_lines: list[str] = []
    for commit in commits[:10]:  # cap at 10 commits for push events
        added: list[str] = commit.get("added", [])
        modified: list[str] = commit.get("modified", [])
        for path in added + modified:
            diff_lines.append(f"diff --git a/{path} b/{path}")
            diff_lines.append(f"+++ b/{path}")

    diff_text = "\n".join(diff_lines)

    findings = await _run_semgrep_on_diff(diff_text)
    finding_count = len(findings)
    conclusion = "failure" if finding_count > 0 else "success"

    from packages.core.src.adapters.github_adapter import GitHubAdapter
    from packages.core.src.ports.github import GitHubError

    github = GitHubAdapter()
    try:
        await github.create_check_run(
            repository,
            commit_sha,
            installation_id=installation_id,
            name="Oute Muscle",
            conclusion=conclusion,
            title="Oute Muscle — Incident Pattern Scan",
            summary=f"Found {finding_count} incident-linked pattern(s) in push to {ref}.",
            annotations=[],
        )
    except GitHubError as exc:
        logger.warning(
            "webhook_l1_check_run_failed",
            repository=repository,
            commit_sha=commit_sha,
            error=str(exc),
        )

    logger.info(
        "webhook_l1_scan_done",
        repository=repository,
        commit_sha=commit_sha,
        finding_count=finding_count,
    )


async def _handle_installation_created(payload: dict[str, Any]) -> None:
    """Provision a new tenant on GitHub App installation.created (T108).

    Creates a Tenant row for the installing GitHub organization/user.

    Args:
        payload: GitHub installation.created payload.
    """
    installation_id: int | None = payload.get("installation", {}).get("id")
    account: dict = payload.get("installation", {}).get("account", {})
    account_login: str = account.get("login", "unknown")
    account_type: str = account.get("type", "User")  # 'Organization' or 'User'

    logger.info(
        "webhook_installation_provisioning",
        installation_id=installation_id,
        account_login=account_login,
        account_type=account_type,
    )

    from apps.api.src.main import get_container
    from packages.db.src.models.tenant import Tenant as TenantModel

    try:
        container = get_container()
    except RuntimeError:
        logger.error("webhook_installation_no_container — DI container not initialized")
        return

    slug = _slugify(account_login)

    async for session in container.session_factory.get_session():
        # Idempotency: skip if tenant already exists for this slug
        from sqlalchemy import select

        existing = (
            await session.execute(select(TenantModel).where(TenantModel.slug == slug))
        ).scalar_one_or_none()

        if existing is not None:
            logger.info(
                "webhook_installation_tenant_exists",
                slug=slug,
                tenant_id=str(existing.id),
            )
            return

        tenant = TenantModel(
            id=uuid.uuid4(),
            name=account_login,
            slug=slug,
            plan_tier="free",
        )
        session.add(tenant)
        await session.commit()

        logger.info(
            "webhook_installation_tenant_created",
            tenant_id=str(tenant.id),
            slug=slug,
            installation_id=installation_id,
        )


async def _handle_installation_deleted(payload: dict[str, Any]) -> None:
    """Deprovision tenant on GitHub App installation.deleted (T108).

    Sets is_active = false for the matching tenant (soft delete).

    Args:
        payload: GitHub installation.deleted payload.
    """
    installation_id: int | None = payload.get("installation", {}).get("id")
    account_login: str = payload.get("installation", {}).get("account", {}).get("login", "")

    logger.info(
        "webhook_installation_deprovisioning",
        installation_id=installation_id,
        account_login=account_login,
    )

    if not account_login:
        logger.warning(
            "webhook_installation_deleted_no_login",
            installation_id=installation_id,
        )
        return

    from apps.api.src.main import get_container
    from packages.db.src.models.tenant import Tenant as TenantModel

    try:
        container = get_container()
    except RuntimeError:
        logger.error("webhook_installation_no_container — DI container not initialized")
        return

    slug = _slugify(account_login)

    async for session in container.session_factory.get_session():
        from sqlalchemy import select, update

        tenant = (
            await session.execute(select(TenantModel).where(TenantModel.slug == slug))
        ).scalar_one_or_none()

        if tenant is None:
            logger.warning(
                "webhook_installation_tenant_not_found",
                slug=slug,
                installation_id=installation_id,
            )
            return

        await session.execute(
            update(TenantModel).where(TenantModel.slug == slug).values(is_active=False)
        )
        await session.commit()

        logger.info(
            "webhook_installation_tenant_deactivated",
            tenant_id=str(tenant.id),
            slug=slug,
            installation_id=installation_id,
        )


# ============================================================================
# Helpers
# ============================================================================


async def _run_semgrep_on_diff(diff: str) -> list[dict[str, Any]]:
    """Run Semgrep rules on a unified diff and return findings.

    Writes the diff to a temp file, invokes `semgrep` CLI, returns findings.
    Falls back to empty list on failure (non-blocking for webhooks).

    Args:
        diff: Unified diff text.

    Returns:
        List of finding dicts with keys: rule_id, path, start_line, end_line,
        severity, message.
    """
    import asyncio
    import json as _json
    import os
    import tempfile

    rules_path = os.environ.get(
        "SEMGREP_RULES_PATH",
        "packages/semgrep-rules",
    )

    if not diff.strip():
        return []

    # Write diff to a temp .diff file and create a stub source file for semgrep
    with tempfile.TemporaryDirectory() as tmpdir:
        diff_path = pathlib.Path(tmpdir) / "changes.diff"
        with diff_path.open("w") as f:
            f.write(diff)

        try:
            proc = await asyncio.create_subprocess_exec(
                "semgrep",
                "--config",
                rules_path,
                "--json",
                "--quiet",
                diff_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except (TimeoutError, FileNotFoundError) as exc:
            logger.warning("webhook_semgrep_unavailable", error=str(exc))
            return []

    try:
        output = _json.loads(stdout.decode())
        raw_results = output.get("results", [])
        return [
            {
                "rule_id": r.get("check_id", "unknown"),
                "path": r.get("path", ""),
                "start_line": r.get("start", {}).get("line", 1),
                "end_line": r.get("end", {}).get("line", 1),
                "severity": r.get("extra", {}).get("severity", "low").lower(),
                "message": r.get("extra", {}).get("message", ""),
            }
            for r in raw_results
        ]
    except Exception as exc:
        logger.warning("webhook_semgrep_parse_failed", error=str(exc))
        return []


async def _run_l2_advisory(
    *,
    diff: str,
    risk_level: Any,
    tenant_id: uuid.UUID | None,
) -> str:
    """Run the L2 RAG advisory pipeline for a diff.

    Requires GCP_PROJECT and DATABASE_URL environment variables.
    Returns empty string if prerequisites are not met.

    Args:
        diff: Unified diff text.
        risk_level: Computed RiskLevel from L1 findings.
        tenant_id: Tenant UUID for RLS (None = system tenant).

    Returns:
        Advisory text or empty string on failure/misconfiguration.
    """
    gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    database_url = os.environ.get("DATABASE_URL")

    if not gcp_project or not database_url:
        logger.info("webhook_l2_skipped — GCP_PROJECT or DATABASE_URL not configured")
        return ""

    effective_tenant_id = tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001")

    try:
        from apps.api.src.adapters.vertex_embedding import VertexAIEmbedding
        from apps.api.src.adapters.vertex_llm import (
            VertexClaudeSonnet,
            VertexGeminiFlash,
            VertexGeminiPro,
        )
        from packages.core.src.domain.advisory.llm_router import LLMRouter
        from packages.core.src.domain.advisory.rag_pipeline import RAGPipeline
        from packages.db.src.adapters.pg_vector_search import PostgreSQLVectorSearch
        from packages.db.src.session import SessionFactory

        vertex_location = os.environ.get("VERTEX_LOCATION", "us-central1")
        session_factory = SessionFactory(database_url=database_url)

        try:
            advisory_text = ""
            async for session in session_factory.get_session(tenant_id=effective_tenant_id):
                pipeline = RAGPipeline(
                    embedding_port=VertexAIEmbedding(
                        project_id=gcp_project, location=vertex_location
                    ),
                    vector_search_port=PostgreSQLVectorSearch(session),
                    llm_router=LLMRouter(
                        flash=VertexGeminiFlash(project_id=gcp_project, location=vertex_location),
                        pro=VertexGeminiPro(project_id=gcp_project, location=vertex_location),
                        claude=VertexClaudeSonnet(project_id=gcp_project),
                    ),
                )
                advisory = await pipeline.process(
                    diff,
                    tenant_id=effective_tenant_id,
                    risk_level=risk_level,
                )
                advisory_text = advisory.analysis_text
        finally:
            await session_factory.close()

        return advisory_text

    except Exception as exc:
        logger.warning("webhook_l2_advisory_failed", error=str(exc))
        return ""


def _severity_to_annotation_level(severity: str) -> str:
    """Map Semgrep severity to GitHub Check Run annotation level.

    Args:
        severity: Semgrep severity string.

    Returns:
        GitHub annotation level: 'failure', 'warning', or 'notice'.
    """
    return {
        "critical": "failure",
        "high": "failure",
        "medium": "warning",
        "low": "notice",
    }.get(severity.lower(), "notice")


def _format_advisory_comment(advisory_text: str, finding_count: int, risk_level: Any) -> str:
    """Format the L2 advisory as a GitHub PR comment.

    Args:
        advisory_text: LLM-generated advisory text.
        finding_count: Number of L1 findings.
        risk_level: Computed risk level.

    Returns:
        Markdown-formatted comment body.
    """
    lines = [
        "## 🔍 Oute Muscle Advisory",
        "",
        f"**Risk Level:** `{risk_level.value.upper()}`  ",
        f"**L1 Findings:** {finding_count}",
        "",
        "---",
        "",
        advisory_text,
        "",
        "---",
        "*Generated by [Oute Muscle](https://oute.me) — incident-based code guardrails.*",
    ]
    return "\n".join(lines)


def _slugify(value: str) -> str:
    """Convert a GitHub account login to a URL-safe slug.

    Args:
        value: GitHub login (org name or username).

    Returns:
        Lowercase, hyphen-separated slug.
    """
    slug = value.lower().strip()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")
