"""Webhook signature verification middleware (T104).

Verifies GitHub webhook X-Hub-Signature-256 header using HMAC-SHA256.
Implements replay protection via delivery UUID deduplication.
"""

from __future__ import annotations

import hashlib
import hmac
from collections import deque


class WebhookSignatureError(Exception):
    """Raised when webhook signature verification fails."""


class WebhookReplayError(Exception):
    """Raised when a webhook replay attack is detected."""


# In-memory cache of recent delivery UUIDs (FIFO, last 1000)
_RECENT_DELIVERY_IDS: deque = deque(maxlen=1000)


def verify_webhook_signature(
    request_body: bytes,
    signature_header: str,
    secret: str,
    delivery_id: str | None = None,
) -> None:
    """Verify GitHub webhook signature and replay protection.

    Args:
        request_body: Raw request body bytes.
        signature_header: X-Hub-Signature-256 header value (format: sha256=<hex>).
        secret: GitHub webhook secret.
        delivery_id: X-GitHub-Delivery header value for replay protection.

    Raises:
        WebhookSignatureError: If signature is invalid or malformed.
        WebhookReplayError: If delivery_id was already seen (replay attack).
    """
    # Verify signature format and validity
    if not signature_header or not signature_header.startswith("sha256="):
        raise WebhookSignatureError(
            "Invalid or missing X-Hub-Signature-256 header (must start with 'sha256=')"
        )

    provided_signature = signature_header[7:]  # Remove "sha256=" prefix

    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise WebhookSignatureError("Webhook signature verification failed")

    # Check for replay attacks if delivery_id is provided
    if delivery_id is not None:
        if delivery_id in _RECENT_DELIVERY_IDS:
            raise WebhookReplayError(
                f"Webhook delivery {delivery_id} already processed (replay detected)"
            )
        _RECENT_DELIVERY_IDS.append(delivery_id)
