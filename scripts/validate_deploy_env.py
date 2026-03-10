from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def parse_port(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Expected integer port, got '{value}'") from exc


def must_equal(errors: list[str], env: dict[str, str], key: str, expected: str) -> None:
    actual = env.get(key, expected)
    if actual != expected:
        errors.append(f"{key} must stay '{expected}' inside Docker network, got '{actual}'.")


def validate_url(errors: list[str], warnings: list[str], key: str, value: str | None) -> None:
    if not value:
        errors.append(f"{key} must be set.")
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{key} must be a valid absolute URL, got '{value}'.")
        return
    if "localhost" in parsed.netloc:
        warnings.append(f"{key} still points to localhost: '{value}'.")


def main() -> int:
    env_path = Path(".env")
    if not env_path.exists():
        print("[ERROR] .env not found. Copy .env.example to .env first.")
        return 1

    env = load_env(env_path)
    errors: list[str] = []
    warnings: list[str] = []

    must_equal(errors, env, "POSTGRES_HOST", "postgres")
    must_equal(errors, env, "POSTGRES_PORT", "5432")
    must_equal(errors, env, "REDIS_HOST", "redis")
    must_equal(errors, env, "REDIS_PORT", "6379")
    must_equal(errors, env, "KEYCLOAK_URL", "http://keycloak:8080")
    must_equal(
        errors,
        env,
        "KEYCLOAK_INTERNAL_JWKS_URL",
        "http://keycloak:8080/realms/ektrm/protocol/openid-connect/certs",
    )

    gateway_port = parse_port(env.get("GATEWAY_PORT"), 8180)
    frontend_port = parse_port(env.get("FRONTEND_PORT"), 9035)
    keycloak_expose_port = parse_port(env.get("KEYCLOAK_EXPOSE_PORT"), 8088)

    for name, port in {
        "GATEWAY_PORT": gateway_port,
        "FRONTEND_PORT": frontend_port,
        "KEYCLOAK_EXPOSE_PORT": keycloak_expose_port,
        "POSTGRES_EXPOSE_PORT": parse_port(env.get("POSTGRES_EXPOSE_PORT"), 6432),
        "REDIS_EXPOSE_PORT": parse_port(env.get("REDIS_EXPOSE_PORT"), 7379),
    }.items():
        if port <= 0 or port > 65535:
            errors.append(f"{name} must be in range 1..65535, got {port}.")

    if len({gateway_port, frontend_port, keycloak_expose_port}) < 3:
        errors.append("GATEWAY_PORT, FRONTEND_PORT, and KEYCLOAK_EXPOSE_PORT must be distinct.")

    app_env = env.get("APP_ENV", "local").strip().lower()
    public_url_keys = [
        "PUBLIC_BASE_URL",
        "KEYCLOAK_ISSUER",
        "KEYCLOAK_JWKS_URL",
        "KEYCLOAK_LOGOUT_URL",
        "FRONTEND_API_BASE",
        "FRONTEND_OIDC_AUTHORITY",
    ]
    for key in public_url_keys:
        if key in env:
            validate_url(errors, warnings, key, env.get(key))

    cors_allowed = env.get("CORS_ALLOWED_ORIGINS", "")
    if not cors_allowed:
        errors.append("CORS_ALLOWED_ORIGINS must be set.")
    elif "localhost" in cors_allowed:
        warnings.append(f"CORS_ALLOWED_ORIGINS still points to localhost: '{cors_allowed}'.")

    if app_env in {"server", "prod", "production"}:
        server_sensitive = [
            "PUBLIC_BASE_URL",
            "KEYCLOAK_ISSUER",
            "KEYCLOAK_JWKS_URL",
            "KEYCLOAK_LOGOUT_URL",
            "FRONTEND_API_BASE",
            "FRONTEND_OIDC_AUTHORITY",
            "CORS_ALLOWED_ORIGINS",
        ]
        for key in server_sensitive:
            value = env.get(key, "")
            if "localhost" in value:
                errors.append(f"{key} cannot point to localhost when APP_ENV={app_env}.")

    if errors:
        print("[ERROR] Deployment env validation failed:")
        for item in errors:
            print(f"- {item}")
        if warnings:
            print("[WARN] Additional findings:")
            for item in warnings:
                print(f"- {item}")
        return 1

    print("[OK] Deployment env validation passed.")
    if warnings:
        print("[WARN] Review these values before server deployment:")
        for item in warnings:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
