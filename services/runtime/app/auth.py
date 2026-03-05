from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError


def _parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AuthSettings:
    enabled: bool
    issuer_allowlist: tuple[str, ...]
    jwks_url: str
    audiences: tuple[str, ...]
    client_id: str
    required_roles: tuple[str, ...]
    algorithms: tuple[str, ...]
    leeway_seconds: int
    jwks_cache_seconds: int


@dataclass(frozen=True)
class CurrentUser:
    subject: str
    username: str
    email: str | None
    roles: frozenset[str]
    claims: dict[str, Any]


class TokenVerifier:
    def __init__(self, settings: AuthSettings) -> None:
        self._settings = settings
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_expires_at = 0.0
        self._jwks_lock = Lock()

    def _load_jwks(self) -> dict[str, Any]:
        request = Request(self._settings.jwks_url, headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=5) as response:
                payload = response.read().decode("utf-8")
        except URLError as exc:  # pragma: no cover - depends on external availability
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC keyset is temporarily unavailable",
            ) from exc

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC keyset response is invalid",
            ) from exc
        if not isinstance(data, dict) or "keys" not in data:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC keyset response is invalid",
            )
        return data

    def _get_jwks(self) -> dict[str, Any]:
        now = time.time()
        if self._jwks_cache and now < self._jwks_expires_at:
            return self._jwks_cache

        with self._jwks_lock:
            now = time.time()
            if self._jwks_cache and now < self._jwks_expires_at:
                return self._jwks_cache
            self._jwks_cache = self._load_jwks()
            self._jwks_expires_at = now + self._settings.jwks_cache_seconds
            return self._jwks_cache

    def _get_signing_key(self, token: str) -> Any:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token format is invalid",
            ) from exc
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token header is missing key id",
            )

        jwks = self._get_jwks()
        keys = jwks.get("keys", [])
        if not isinstance(keys, list):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC keyset format is invalid",
            )

        for key_data in keys:
            if isinstance(key_data, dict) and key_data.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signing key is not recognized",
        )

    def verify(self, token: str) -> dict[str, Any]:
        signing_key = self._get_signing_key(token)
        try:
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=list(self._settings.algorithms),
                audience=list(self._settings.audiences),
                options={"require": ["exp", "iat"]},
                leeway=self._settings.leeway_seconds,
            )
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token is invalid or expired",
            ) from exc

        issuer = claims.get("iss")
        if issuer not in self._settings.issuer_allowlist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer is not allowed",
            )
        return claims


def _build_settings() -> AuthSettings:
    enabled = _env_bool("AUTH_REQUIRED", True)
    issuer_allowlist = _parse_csv(
        os.getenv(
            "KEYCLOAK_ALLOWED_ISSUERS",
            os.getenv("KEYCLOAK_ISSUER", "http://localhost:8088/realms/ektrm"),
        )
    )
    audiences = _parse_csv(os.getenv("KEYCLOAK_AUDIENCE", "ektrm-api"))
    required_roles = _parse_csv(os.getenv("KEYCLOAK_REQUIRED_ROLES", "Applicant,OPS"))
    algorithms = _parse_csv(os.getenv("KEYCLOAK_ALGORITHMS", "RS256"))
    jwks_url = os.getenv(
        "KEYCLOAK_JWKS_URL",
        "http://keycloak:8080/realms/ektrm/protocol/openid-connect/certs",
    )
    client_id = os.getenv("KEYCLOAK_CLIENT_ID", "ektrm-web")
    leeway_seconds = int(os.getenv("KEYCLOAK_LEEWAY_SECONDS", "10"))
    jwks_cache_seconds = int(os.getenv("KEYCLOAK_JWKS_CACHE_SECONDS", "300"))

    if enabled and not issuer_allowlist:
        raise RuntimeError("KEYCLOAK_ISSUER/KEYCLOAK_ALLOWED_ISSUERS must be configured")
    if enabled and not audiences:
        raise RuntimeError("KEYCLOAK_AUDIENCE must be configured")

    return AuthSettings(
        enabled=enabled,
        issuer_allowlist=issuer_allowlist,
        jwks_url=jwks_url,
        audiences=audiences,
        client_id=client_id,
        required_roles=required_roles,
        algorithms=algorithms,
        leeway_seconds=leeway_seconds,
        jwks_cache_seconds=jwks_cache_seconds,
    )


AUTH_SETTINGS = _build_settings()
TOKEN_VERIFIER = TokenVerifier(AUTH_SETTINGS)
HTTP_BEARER = HTTPBearer(auto_error=False)


def extract_roles(claims: dict[str, Any], client_id: str) -> frozenset[str]:
    roles: set[str] = set()
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        raw_realm_roles = realm_access.get("roles", [])
        if isinstance(raw_realm_roles, list):
            roles.update(str(role) for role in raw_realm_roles)

    resource_access = claims.get("resource_access")
    if isinstance(resource_access, dict):
        client_access = resource_access.get(client_id, {})
        if isinstance(client_access, dict):
            raw_client_roles = client_access.get("roles", [])
            if isinstance(raw_client_roles, list):
                roles.update(str(role) for role in raw_client_roles)

    return frozenset(roles)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTP_BEARER),
) -> CurrentUser:
    if not AUTH_SETTINGS.enabled:
        return CurrentUser(
            subject="auth-disabled",
            username="anonymous",
            email=None,
            roles=frozenset(),
            claims={},
        )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
        )

    claims = TOKEN_VERIFIER.verify(token)
    roles = extract_roles(claims, AUTH_SETTINGS.client_id)
    username = str(claims.get("preferred_username", claims.get("sub", "")))
    email = claims.get("email")
    if email is not None:
        email = str(email)
    subject_value = claims.get("sub") or claims.get("preferred_username") or claims.get("jti")
    return CurrentUser(
        subject=str(subject_value),
        username=username,
        email=email,
        roles=roles,
        claims=claims,
    )


def require_roles(*required_roles: str):
    required_set = {role for role in required_roles if role}

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not AUTH_SETTINGS.enabled:
            return user
        if not required_set.issubset(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role does not allow this action",
            )
        return user

    return _dependency
