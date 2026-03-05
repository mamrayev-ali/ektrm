import os
import socket
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AUTH_SETTINGS, CurrentUser, get_current_user, require_roles
from app.routers.applications import router as applications_router
from app.routers.files import router as files_router
from app.routers.reference_data import router as reference_data_router

app = FastAPI(title="e-KTRM Runtime Service", version="0.1.0")

SERVICE_NAME = os.getenv("SERVICE_NAME", "runtime-service")
APP_ENV = os.getenv("APP_ENV", "local")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REFERENCE_DATA_SERVICES = {"reference-data-service", "gateway-service"}
APPLICATION_SERVICES = {"applications-service", "gateway-service"}
FILE_SERVICES = {"files-service", "gateway-service"}


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_csv(os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:4200")),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

if SERVICE_NAME in REFERENCE_DATA_SERVICES:
    app.include_router(reference_data_router)

if SERVICE_NAME in APPLICATION_SERVICES:
    app.include_router(applications_router)

if SERVICE_NAME in FILE_SERVICES:
    app.include_router(files_router)


def _check_tcp(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _readiness_checks() -> dict[str, bool]:
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))

    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_host, minio_port = minio_endpoint.split(":", 1)

    keycloak_url = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    keycloak_host_port = keycloak_url.split("//", 1)[-1]
    keycloak_host, keycloak_port = keycloak_host_port.split(":", 1)

    return {
        "postgres": _check_tcp(postgres_host, postgres_port),
        "redis": _check_tcp(redis_host, redis_port),
        "minio": _check_tcp(minio_host, int(minio_port)),
        "keycloak": _check_tcp(keycloak_host, int(keycloak_port)),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "environment": APP_ENV,
        "log_level": LOG_LEVEL,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }


@app.get("/auth/config")
def auth_config() -> dict[str, object]:
    return {
        "enabled": AUTH_SETTINGS.enabled,
        "issuer_allowlist": list(AUTH_SETTINGS.issuer_allowlist),
        "audiences": list(AUTH_SETTINGS.audiences),
        "client_id": AUTH_SETTINGS.client_id,
        "required_roles": list(AUTH_SETTINGS.required_roles),
    }


@app.get("/auth/me")
def auth_me(current_user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    return {
        "subject": current_user.subject,
        "username": current_user.username,
        "email": current_user.email,
        "roles": sorted(current_user.roles),
    }


@app.get("/auth/applicant-area")
def applicant_area(
    current_user: CurrentUser = Depends(require_roles("Applicant")),
) -> dict[str, object]:
    return {
        "message": "Applicant access granted",
        "subject": current_user.subject,
        "username": current_user.username,
        "roles": sorted(current_user.roles),
    }


@app.get("/auth/ops-area")
def ops_area(
    current_user: CurrentUser = Depends(require_roles("OPS")),
) -> dict[str, object]:
    return {
        "message": "OPS access granted",
        "subject": current_user.subject,
        "username": current_user.username,
        "roles": sorted(current_user.roles),
    }


@app.get("/readiness")
def readiness() -> dict[str, object]:
    checks = _readiness_checks()
    if not all(checks.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "service": SERVICE_NAME, "checks": checks},
        )

    return {
        "status": "ready",
        "service": SERVICE_NAME,
        "checks": checks,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
