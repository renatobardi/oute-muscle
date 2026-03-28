"""OAuth 2.1 + PKCE unit tests."""

import base64
import hashlib
import time
import uuid

import pytest

from apps.mcp.src.auth.provider import (
    JWTExpiredError,
    JWTInvalidError,
    OAuthError,
    OAuthProvider,
)


def test_authorize_returns_auth_code():
    """GET /oauth/authorize with code_challenge → returns auth code."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())
    code_challenge = "e9Mrozoa2owUe2JVgzlAMaC8zQ91Xo-gBtlMXoUN84M"

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    assert auth_code is not None
    assert isinstance(auth_code, str)
    assert len(auth_code) > 0


def test_token_exchange_valid_pkce():
    """POST /oauth/token with correct code_verifier → returns JWT access token."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    # Generate a valid code_verifier and code_challenge
    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    # Exchange with correct verifier
    access_token, refresh_token = provider.exchange_code(
        code=auth_code, code_verifier=code_verifier
    )

    assert access_token is not None
    assert refresh_token is not None
    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)


def test_token_exchange_wrong_verifier_fails():
    """wrong verifier → raises OAuthError."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    # Exchange with wrong verifier
    wrong_verifier = "wrong_verifier_value_1234567890123456"
    with pytest.raises(OAuthError):
        provider.exchange_code(code=auth_code, code_verifier=wrong_verifier)


def test_token_exchange_expired_code_fails():
    """expired auth code → raises OAuthError."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    # Manually expire the code by manipulating internal state
    if auth_code in provider._auth_codes:
        provider._auth_codes[auth_code]["expiry"] = time.time() - 1

    with pytest.raises(OAuthError):
        provider.exchange_code(code=auth_code, code_verifier=code_verifier)


def test_refresh_token_returns_new_access_token():
    """valid refresh_token → new access token."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    _, refresh_token = provider.exchange_code(
        code=auth_code, code_verifier=code_verifier
    )

    new_access_token = provider.refresh_access_token(refresh_token)

    assert new_access_token is not None
    assert isinstance(new_access_token, str)
    # New token should be valid
    claims = provider.validate_jwt(new_access_token)
    assert claims["sub"] == user_id


def test_refresh_token_invalid_fails():
    """invalid refresh_token → raises OAuthError."""
    provider = OAuthProvider()

    with pytest.raises(OAuthError):
        provider.refresh_access_token("invalid_refresh_token_value")


def test_jwt_validation_valid_token():
    """valid RS256 JWT → returns claims dict."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    access_token, _ = provider.exchange_code(
        code=auth_code, code_verifier=code_verifier
    )

    claims = provider.validate_jwt(access_token)

    assert claims is not None
    assert isinstance(claims, dict)
    assert "sub" in claims
    assert "iat" in claims
    assert "exp" in claims


def test_jwt_validation_expired_fails():
    """expired token → raises JWTExpiredError."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    _, _ = provider.exchange_code(
        code=auth_code, code_verifier=code_verifier
    )

    # Manually create an expired token
    import jwt
    expired_payload = {"sub": user_id, "exp": int(time.time()) - 100}
    expired_token = jwt.encode(
        expired_payload, provider._private_key, algorithm="RS256"
    )

    with pytest.raises(JWTExpiredError):
        provider.validate_jwt(expired_token)


def test_jwt_validation_invalid_signature_fails():
    """tampered token → raises JWTInvalidError."""
    provider = OAuthProvider()

    tampered_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyX2lkIn0.invalid_signature"

    with pytest.raises((JWTInvalidError, OAuthError)):
        provider.validate_jwt(tampered_token)


def test_pkce_s256_challenge_verified():
    """S256 method: SHA256(verifier)|base64url == challenge."""
    provider = OAuthProvider()
    user_id = str(uuid.uuid4())

    code_verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    # Manually compute expected challenge
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    auth_code = provider.generate_auth_code(
        user_id=user_id,
        code_challenge=expected_challenge,
        code_challenge_method="S256",
    )

    # Should succeed with correct verifier
    access_token, refresh_token = provider.exchange_code(
        code=auth_code, code_verifier=code_verifier
    )

    assert access_token is not None
    assert refresh_token is not None
