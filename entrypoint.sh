#!/usr/bin/env bash
set -euo pipefail

cd /app
export PYTHONPATH=/app:${PYTHONPATH:-}

PORT="${APP_PORT:-7003}"
LOG_LEVEL="${LOG_LEVEL:-info}"

UVICORN_CMD=(
    /opt/venv/bin/uvicorn
    app.main:app
    --host
    0.0.0.0
    --port
    "${PORT}"
    --log-level
    "${LOG_LEVEL}"
)

if [[ -n "${TLS_CERT_FILE:-}" && -n "${TLS_KEY_FILE:-}" ]]; then
    if [[ ! -f "${TLS_CERT_FILE}" || ! -f "${TLS_KEY_FILE}" ]]; then
        echo "TLS configuration requested but certificate or key is missing. Falling back to HTTP..." >&2
    else
        UVICORN_CMD+=(
            --ssl-certfile
            "${TLS_CERT_FILE}"
            --ssl-keyfile
            "${TLS_KEY_FILE}"
        )

        if [[ -n "${TLS_CA_BUNDLE:-}" ]]; then
            if [[ ! -f "${TLS_CA_BUNDLE}" ]]; then
                echo "TLS CA bundle file not found: ${TLS_CA_BUNDLE}" >&2
                exit 1
            fi
            UVICORN_CMD+=(
                --ssl-ca-certs
                "${TLS_CA_BUNDLE}"
            )
        fi
    fi
fi

exec "${UVICORN_CMD[@]}"
