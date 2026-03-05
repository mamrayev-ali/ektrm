import os
import socket
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

app = FastAPI(title="e-KTRM Runtime Service", version="0.1.0")

SERVICE_NAME = os.getenv("SERVICE_NAME", "runtime-service")
APP_ENV = os.getenv("APP_ENV", "local")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


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
