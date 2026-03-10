#!/bin/sh
set -eu

cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.__EKTRM_RUNTIME_CONFIG__ = {
  apiBase: "${FRONTEND_API_BASE:-}",
  oidcAuthority: "${FRONTEND_OIDC_AUTHORITY:-}",
  oidcClientId: "${FRONTEND_OIDC_CLIENT_ID:-ektrm-web}",
  apiPort: "${FRONTEND_GATEWAY_PORT:-8180}",
  oidcPort: "${FRONTEND_KEYCLOAK_PORT:-8088}"
};
EOF
