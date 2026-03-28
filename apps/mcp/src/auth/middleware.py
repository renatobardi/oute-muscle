"""OAuth 2.1 JWT validation middleware."""

from __future__ import annotations

from apps.mcp.src.auth.provider import JWTExpiredError, JWTInvalidError, OAuthProvider


class AuthMiddlewareError(Exception):
    """Base auth middleware error."""

    pass


class MissingTokenError(AuthMiddlewareError):
    """Missing authorization token."""

    pass


class InvalidTokenError(AuthMiddlewareError):
    """Invalid or expired token."""

    pass


def extract_claims(authorization_header: str | None, provider: OAuthProvider) -> dict:
    """Extract and validate JWT claims from Authorization header.

    Args:
        authorization_header: Value of Authorization header (e.g., "Bearer <token>")
        provider: OAuthProvider instance for validation

    Returns:
        Decoded claims dict

    Raises:
        MissingTokenError: If token is missing
        InvalidTokenError: If token is invalid or expired
    """
    if not authorization_header:
        raise MissingTokenError("Missing Authorization header")

    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise MissingTokenError("Invalid Authorization header format")

    token = parts[1]

    try:
        claims = provider.validate_jwt(token)
        return claims
    except JWTExpiredError as e:
        raise InvalidTokenError(f"Token expired: {e}") from e
    except JWTInvalidError as e:
        raise InvalidTokenError(f"Invalid token: {e}") from e
