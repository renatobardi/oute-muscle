"""OAuth 2.1 provider with PKCE.

In-memory storage for auth codes (dict mapping code → {verifier_challenge, expiry, user_id}).
Auth codes expire in 10 minutes.
Refresh tokens expire in 30 days.

JWT claims: { sub: user_id, tenant_id: str, tier: str, iat: int, exp: int }
RS256 signing: use PyJWT with generated RSA key pair (store in memory for tests).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class OAuthError(Exception):
    """Base OAuth error."""

    pass


class JWTExpiredError(OAuthError):
    """JWT token has expired."""

    pass


class JWTInvalidError(OAuthError):
    """JWT token is invalid or signature verification failed."""

    pass


class OAuthProvider:
    """OAuth 2.1 provider with PKCE support.

    In-memory implementation suitable for testing.
    Production would use Redis or PostgreSQL for persistence.
    """

    AUTH_CODE_EXPIRY_SECONDS = 10 * 60  # 10 minutes
    REFRESH_TOKEN_EXPIRY_SECONDS = 30 * 24 * 60 * 60  # 30 days
    ACCESS_TOKEN_EXPIRY_SECONDS = 60 * 60  # 1 hour

    def __init__(self) -> None:
        """Initialize OAuth provider with RSA key pair."""
        # Generate RSA key pair for JWT signing (RS256)
        self._private_key_obj = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        self._private_key = self._private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        self._public_key = self._private_key_obj.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        # In-memory storage
        self._auth_codes: dict[str, dict] = {}
        self._refresh_tokens: dict[str, dict] = {}

    def generate_auth_code(
        self,
        user_id: str,
        code_challenge: str,
        code_challenge_method: str,
    ) -> str:
        """Generate an authorization code.

        Args:
            user_id: User identifier
            code_challenge: PKCE code challenge
            code_challenge_method: "S256" or "plain"

        Returns:
            Authorization code
        """
        auth_code = secrets.token_urlsafe(32)
        self._auth_codes[auth_code] = {
            "user_id": user_id,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "expiry": time.time() + self.AUTH_CODE_EXPIRY_SECONDS,
        }
        return auth_code

    def exchange_code(self, code: str, code_verifier: str) -> tuple[str, str]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code
            code_verifier: PKCE code verifier

        Returns:
            Tuple of (access_token, refresh_token)

        Raises:
            OAuthError: If code is invalid, expired, or verifier doesn't match
        """
        if code not in self._auth_codes:
            raise OAuthError("Invalid authorization code")

        auth_entry = self._auth_codes[code]

        # Check expiry
        if time.time() > auth_entry["expiry"]:
            del self._auth_codes[code]
            raise OAuthError("Authorization code expired")

        # Verify PKCE
        if auth_entry["code_challenge_method"] == "S256":
            computed_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()
            if computed_challenge != auth_entry["code_challenge"]:
                raise OAuthError("PKCE verification failed")
        elif auth_entry["code_challenge_method"] == "plain":
            if code_verifier != auth_entry["code_challenge"]:
                raise OAuthError("PKCE verification failed")

        # Generate tokens
        user_id = auth_entry["user_id"]
        access_token = self._generate_access_token(user_id)
        refresh_token = self._generate_refresh_token(user_id)

        # Store refresh token
        self._refresh_tokens[refresh_token] = {
            "user_id": user_id,
            "expiry": time.time() + self.REFRESH_TOKEN_EXPIRY_SECONDS,
        }

        # Remove used auth code
        del self._auth_codes[code]

        return access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> str:
        """Generate a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token

        Raises:
            OAuthError: If refresh token is invalid or expired
        """
        if refresh_token not in self._refresh_tokens:
            raise OAuthError("Invalid refresh token")

        token_entry = self._refresh_tokens[refresh_token]

        # Check expiry
        if time.time() > token_entry["expiry"]:
            del self._refresh_tokens[refresh_token]
            raise OAuthError("Refresh token expired")

        user_id = token_entry["user_id"]
        return self._generate_access_token(user_id)

    def validate_jwt(self, token: str) -> dict:
        """Validate and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded claims dict

        Raises:
            JWTExpiredError: If token has expired
            JWTInvalidError: If token signature is invalid
        """
        try:
            claims = jwt.decode(
                token, self._public_key, algorithms=["RS256"]
            )
            return claims
        except jwt.ExpiredSignatureError as e:
            raise JWTExpiredError(str(e)) from e
        except (jwt.InvalidSignatureError, jwt.InvalidTokenError) as e:
            raise JWTInvalidError(str(e)) from e

    def _generate_access_token(self, user_id: str) -> str:
        """Generate an access token.

        Args:
            user_id: User identifier

        Returns:
            JWT access token
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=self.ACCESS_TOKEN_EXPIRY_SECONDS)

        payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
        }

        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def _generate_refresh_token(self, user_id: str) -> str:
        """Generate a refresh token.

        Args:
            user_id: User identifier

        Returns:
            Refresh token (opaque string)
        """
        return secrets.token_urlsafe(32)
