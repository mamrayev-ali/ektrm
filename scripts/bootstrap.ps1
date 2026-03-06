param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

Write-Host "Starting e-KTRM platform containers..."
docker compose up -d --build

Write-Host "Applying Alembic migrations..."
docker compose run --rm --no-deps gateway-service python -m alembic -c /app/alembic.ini upgrade head

Write-Host "Synchronizing seeded reference data..."
docker compose run --rm --no-deps gateway-service python -m app.seed.reference_data_sync

Write-Host ""
Write-Host "Service health endpoints:"
$ports = @{
  "gateway-service"      = if ($env:GATEWAY_PORT) { $env:GATEWAY_PORT } else { "8080" }
  "applications-service" = if ($env:APPLICATIONS_PORT) { $env:APPLICATIONS_PORT } else { "8081" }
  "certificates-service" = if ($env:CERTIFICATES_PORT) { $env:CERTIFICATES_PORT } else { "8082" }
  "reference-data-service" = if ($env:REFERENCE_DATA_PORT) { $env:REFERENCE_DATA_PORT } else { "8083" }
  "files-service" = if ($env:FILES_PORT) { $env:FILES_PORT } else { "8084" }
  "notifications-service" = if ($env:NOTIFICATIONS_PORT) { $env:NOTIFICATIONS_PORT } else { "8085" }
  "frontend" = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "4200" }
}

foreach ($service in $ports.Keys) {
  Write-Host "- $service`: http://localhost:$($ports[$service])/health"
}
