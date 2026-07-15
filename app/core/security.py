from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390_000
JWT_ALGORITHM = "HS256"
JWT_HEADER = {"alg": JWT_ALGORITHM, "typ": "JWT"}


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _json_b64encode(payload: dict[str, Any]) -> str:
    return _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")
    if iterations <= 0:
        raise ValueError("Iterations must be positive.")

    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations,
    )
    return f"{PASSWORD_ALGORITHM}${iterations}${_b64encode(salt_bytes)}${_b64encode(digest)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_value, salt_value, digest_value = encoded_hash.split("$")
    except ValueError:
        return False

    if algorithm != PASSWORD_ALGORITHM:
        return False

    try:
        iterations = int(iterations_value)
        salt = _b64decode(salt_value)
        expected_digest = _b64decode(digest_value)
    except (TypeError, ValueError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)


def build_token_claims(
    *,
    subject: str,
    email: str,
    role: str,
    token_type: str,
    expires_in_seconds: int,
    issued_at: int | None = None,
) -> dict[str, Any]:
    issued_at_value = int(time.time()) if issued_at is None else int(issued_at)
    claims = {
        "sub": subject,
        "email": email,
        "role": role,
        "token_type": token_type,
        "iat": issued_at_value,
        "exp": issued_at_value + int(expires_in_seconds),
        "jti": secrets.token_urlsafe(16),
    }
    return claims


def encode_token(claims: dict[str, Any], secret: str) -> str:
    header_segment = _json_b64encode(JWT_HEADER)
    payload_segment = _json_b64encode(claims)
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64encode(signature)}"


def decode_token(
    token: str,
    secret: str,
    *,
    expected_token_type: str | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise ValueError("Token must contain exactly three segments.") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()

    try:
        provided_signature = _b64decode(signature_segment)
    except ValueError as exc:
        raise ValueError("Token signature is malformed.") from exc

    if not hmac.compare_digest(provided_signature, expected_signature):
        raise ValueError("Token signature is invalid.")

    try:
        header = json.loads(_b64decode(header_segment))
        payload = json.loads(_b64decode(payload_segment))
    except json.JSONDecodeError as exc:
        raise ValueError("Token payload is malformed.") from exc

    if header.get("alg") != JWT_ALGORITHM:
        raise ValueError("Unsupported token algorithm.")

    if expected_token_type is not None and payload.get("token_type") != expected_token_type:
        raise ValueError("Token type is invalid.")

    current_time = int(time.time()) if now is None else int(now)
    expires_at = int(payload.get("exp", 0))
    if expires_at <= current_time:
        raise ValueError("Token has expired.")

    return payload
