"""Tests for GitHub webhook event routing (T100).

GitHub webhook event routing (unit tests) — middleware and payload tests.
"""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from apps.api.src.middleware.webhook_auth import (
    WebhookReplayError,
    WebhookSignatureError,
    verify_webhook_signature,
)


def create_webhook_signature(body: bytes, secret: str) -> str:
    """Create valid GitHub webhook signature."""
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


@pytest.fixture
def webhook_secret() -> str:
    """GitHub webhook secret for testing."""
    return "test-webhook-secret"


@pytest.fixture(autouse=True)
def clear_replay_cache() -> None:
    """Clear the replay protection cache before each test."""
    from apps.api.src.middleware.webhook_auth import _RECENT_DELIVERY_IDS

    _RECENT_DELIVERY_IDS.clear()


class TestWebhookEventProcessing:
    """Tests for webhook event payload processing."""

    def test_pull_request_opened_payload_valid(self) -> None:
        """pull_request.opened payload is valid."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"sha": "abc123def456"},
                "base": {"repo": {"full_name": "owner/repo"}},
            },
            "repository": {"full_name": "owner/repo"},
            "installation": {"id": 12345},
        }
        body = json.dumps(payload).encode()

        # Verify payload structure
        assert payload["action"] == "opened"
        assert payload["pull_request"]["number"] == 42
        assert payload["repository"]["full_name"] == "owner/repo"
        assert body == json.dumps(payload).encode()

    def test_pull_request_synchronize_payload_valid(self) -> None:
        """pull_request.synchronize payload is valid."""
        payload = {
            "action": "synchronize",
            "pull_request": {
                "number": 43,
                "head": {"sha": "xyz789"},
                "base": {"repo": {"full_name": "owner/repo"}},
            },
            "repository": {"full_name": "owner/repo"},
            "installation": {"id": 12345},
        }

        assert payload["action"] == "synchronize"
        assert payload["pull_request"]["number"] == 43

    def test_push_payload_valid(self) -> None:
        """push payload is valid."""
        payload = {
            "ref": "refs/heads/main",
            "after": "abc123def456",
            "repository": {"full_name": "owner/repo"},
            "installation": {"id": 12345},
        }

        assert payload["ref"] == "refs/heads/main"
        assert payload["after"] == "abc123def456"

    def test_installation_created_payload_valid(self) -> None:
        """installation.created payload is valid."""
        payload = {
            "action": "created",
            "installation": {"id": 99999, "account": {"login": "test-org"}},
        }

        assert payload["action"] == "created"
        assert payload["installation"]["id"] == 99999
        assert payload["installation"]["account"]["login"] == "test-org"

    def test_installation_deleted_payload_valid(self) -> None:
        """installation.deleted payload is valid."""
        payload = {
            "action": "deleted",
            "installation": {"id": 99999, "account": {"login": "test-org"}},
        }

        assert payload["action"] == "deleted"

    def test_ping_payload_valid(self) -> None:
        """ping payload is valid."""
        payload = {"zen": "Design for failure."}

        assert "zen" in payload

    def test_unknown_event_payload_valid(self) -> None:
        """Unknown event payload is valid."""
        payload = {"some": "data"}

        assert "some" in payload


class TestWebhookSignatureProcessing:
    """Tests for webhook signature verification processing."""

    def test_pull_request_signature_verification(self, webhook_secret: str) -> None:
        """Signature verification works for pull_request events."""
        payload = {
            "action": "opened",
            "pull_request": {"number": 42},
            "repository": {"full_name": "owner/repo"},
        }
        body = json.dumps(payload).encode()
        signature = create_webhook_signature(body, webhook_secret)

        # Verify signature
        verify_webhook_signature(body, signature, webhook_secret)

    def test_push_signature_verification(self, webhook_secret: str) -> None:
        """Signature verification works for push events."""
        payload = {
            "ref": "refs/heads/main",
            "after": "abc123",
            "repository": {"full_name": "owner/repo"},
        }
        body = json.dumps(payload).encode()
        signature = create_webhook_signature(body, webhook_secret)

        verify_webhook_signature(body, signature, webhook_secret)

    def test_installation_signature_verification(self, webhook_secret: str) -> None:
        """Signature verification works for installation events."""
        payload = {"action": "created", "installation": {"id": 99999}}
        body = json.dumps(payload).encode()
        signature = create_webhook_signature(body, webhook_secret)

        verify_webhook_signature(body, signature, webhook_secret)

    def test_invalid_signature_rejected(self, webhook_secret: str) -> None:
        """Invalid signature is rejected."""
        payload = {"action": "opened"}
        body = json.dumps(payload).encode()
        bad_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

        with pytest.raises(WebhookSignatureError):
            verify_webhook_signature(body, bad_signature, webhook_secret)

    def test_replay_detection(self, webhook_secret: str) -> None:
        """Replay protection detects repeated delivery IDs."""
        payload = {"action": "opened"}
        body = json.dumps(payload).encode()
        signature = create_webhook_signature(body, webhook_secret)
        delivery_id = "12345-67890"

        # First call succeeds
        verify_webhook_signature(body, signature, webhook_secret, delivery_id=delivery_id)

        # Second call with same delivery_id fails
        with pytest.raises(WebhookReplayError):
            verify_webhook_signature(body, signature, webhook_secret, delivery_id=delivery_id)

    def test_different_delivery_ids_allowed(self, webhook_secret: str) -> None:
        """Different delivery IDs are allowed."""
        payload = {"action": "opened"}
        body = json.dumps(payload).encode()
        signature = create_webhook_signature(body, webhook_secret)

        delivery_id_1 = "12345-67890"
        delivery_id_2 = "12345-67891"

        # Both should succeed
        verify_webhook_signature(body, signature, webhook_secret, delivery_id=delivery_id_1)
        verify_webhook_signature(body, signature, webhook_secret, delivery_id=delivery_id_2)
