#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Starting e-KTRM platform containers..."
docker compose up -d --build

echo "\nService health endpoints:"
endpoints=(
  "gateway-service:${GATEWAY_PORT:-8080}"
  "applications-service:${APPLICATIONS_PORT:-8081}"
  "certificates-service:${CERTIFICATES_PORT:-8082}"
  "reference-data-service:${REFERENCE_DATA_PORT:-8083}"
  "files-service:${FILES_PORT:-8084}"
  "notifications-service:${NOTIFICATIONS_PORT:-8085}"
  "frontend:${FRONTEND_PORT:-4200}"
)

for item in "${endpoints[@]}"; do
  name="${item%%:*}"
  port="${item##*:}"
  echo "- $name: http://localhost:${port}/health"
done
