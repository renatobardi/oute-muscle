"""GitHub webhook routes (T105-T108).

POST /v1/webhooks/github — Main webhook endpoint
  - Verifies signature (webhook_auth middleware)
  - Routes based on X-GitHub-Event header:
    - 'pull_request' (action: opened/synchronize) → L1+L2 pipeline
    - 'push' → L1 scan pipeline
    - 'installation' (action: created/deleted) → tenant provisioning
    - 'ping' → return 200 {"status": "pong"}
    - unknown → return 200 {"status": "ignored"}
  - Always returns 200 immediately
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
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
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(default=None, alias="X-GitHub-Delivery"),
) -> WebhookResponse:
    """Handle GitHub webhook events.

    Verifies signature, routes to appropriate pipeline, returns 200 immediately.

    Args:
        request: FastAPI request object.
        x_github_event: X-GitHub-Event header (e.g., 'pull_request', 'push').
        x_hub_signature_256: X-Hub-Signature-256 header (HMAC-SHA256 signature).
        x_github_delivery: X-GitHub-Delivery header (delivery UUID for replay protection).

    Returns:
        WebhookResponse with status (queued, pong, ignored, error).
    """
    # Get raw body
    body = await request.body()

    # Verify webhook signature
    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("GITHUB_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        verify_webhook_signature(
            body, x_hub_signature_256, webhook_secret, delivery_id=x_github_delivery
        )
    except WebhookSignatureError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized") from e
    except WebhookReplayError as e:
        logger.warning(f"Webhook replay attack detected: {e}")
        # Return 200 to not trigger GitHub retries, but log the attempt
        return WebhookResponse(status="ignored", delivery_id=x_github_delivery)

    # Parse payload
    try:
        payload = json.loads(body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    # Route based on event type
    if x_github_event == "ping":
        logger.info("Received GitHub ping event")
        return WebhookResponse(status="pong", delivery_id=x_github_delivery)

    elif x_github_event == "pull_request":
        action = payload.get("action")
        if action in ("opened", "synchronize"):
            logger.info(f"Received pull_request event (action={action}), queuing L1+L2 pipeline")
            await _run_l1_and_l2_pipeline(payload)
            return WebhookResponse(status="queued", delivery_id=x_github_delivery)
        else:
            logger.info(f"Ignoring pull_request event with action={action}")
            return WebhookResponse(status="ignored", delivery_id=x_github_delivery)

    elif x_github_event == "push":
        logger.info("Received push event, queuing L1 scan pipeline")
        await _run_l1_scan(payload)
        return WebhookResponse(status="queued", delivery_id=x_github_delivery)

    elif x_github_event == "installation":
        action = payload.get("action")
        if action == "created":
            logger.info("Received installation.created event, provisioning tenant")
            await _handle_installation_created(payload)
            return WebhookResponse(status="queued", delivery_id=x_github_delivery)
        elif action == "deleted":
            logger.info("Received installation.deleted event, deprovisioning tenant")
            await _handle_installation_deleted(payload)
            return WebhookResponse(status="queued", delivery_id=x_github_delivery)

    else:
        logger.info(f"Unknown event type: {x_github_event}")
        return WebhookResponse(status="ignored", delivery_id=x_github_delivery)


# ============================================================================
# Pipeline handlers (T106-T108)
# ============================================================================


async def _run_l1_and_l2_pipeline(payload: dict[str, Any]) -> None:
    """Run Layer 1 and Layer 2 pipelines on PR event (T107).

    Steps:
      1. Extract repo, PR number, commit SHA
      2. Run Semgrep rules on diff
      3. Create Check Run
      4. Compute risk score
      5. Run RAG advisory pipeline
      6. Post advisory as PR comment

    Args:
        payload: GitHub webhook payload.
    """
    repository = payload.get("repository", {}).get("full_name")
    pr_number = payload.get("pull_request", {}).get("number")
    commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha")

    logger.info(f"L1+L2 pipeline queued for {repository}#{pr_number} (commit={commit_sha})")
    # TODO: Implement actual pipeline
    # 1. Get PR diff
    # 2. Run L1 scan (Semgrep)
    # 3. Create Check Run
    # 4. Run L2 RAG advisory
    # 5. Post advisory comments
    pass


async def _run_l1_scan(payload: dict[str, Any]) -> None:
    """Run Layer 1 scan pipeline on push event (T106).

    Steps:
      1. Extract repo and commit SHA from payload
      2. Run Semgrep rules on diff (stub for now)
      3. Create Check Run with SARIF annotations

    Args:
        payload: GitHub webhook payload.
    """
    repository = payload.get("repository", {}).get("full_name")
    commit_sha = payload.get("after")
    ref = payload.get("ref")

    logger.info(f"L1 scan queued for {repository}@{commit_sha} (ref={ref})")
    # TODO: Implement actual L1 scan
    # 1. Get commit diff
    # 2. Run Semgrep rules
    # 3. Create Check Run
    pass


async def _handle_installation_created(payload: dict[str, Any]) -> None:
    """Handle GitHub App installation.created event (T108).

    Provisions a new tenant in the system.

    Args:
        payload: GitHub webhook payload.
    """
    installation_id = payload.get("installation", {}).get("id")
    account_login = payload.get("installation", {}).get("account", {}).get("login")

    logger.info(f"Tenant provisioned: {account_login} installation={installation_id}")
    # TODO: Create Tenant record in DB with GitHub App installation ID
    pass


async def _handle_installation_deleted(payload: dict[str, Any]) -> None:
    """Handle GitHub App installation.deleted event (T108).

    Deprovisions a tenant from the system.

    Args:
        payload: GitHub webhook payload.
    """
    installation_id = payload.get("installation", {}).get("id")

    logger.info(f"Tenant deprovisioned: installation={installation_id}")
    # TODO: Soft-delete Tenant record from DB
    pass
