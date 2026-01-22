#!/usr/bin/env bash
set -euo pipefail

cd /app
export PYTHONPATH=/app:${PYTHONPATH:-}

PORT="${APP_PORT:-7003}"
LOG_LEVEL="${LOG_LEVEL:-info}"
DEFAULT_WORKERS="$(
    python - <<'PY'
import multiprocessing
try:
    cpu_count = multiprocessing.cpu_count()
except NotImplementedError:
    cpu_count = 1
print(max(2, cpu_count))
PY
)"
WORKERS="${WEB_CONCURRENCY:-${DEFAULT_WORKERS}}"

UVICORN_CMD=(
    /opt/venv/bin/uvicorn
    app.main:app
    --host
    0.0.0.0
    --port
    "${PORT}"
    --log-level
    "${LOG_LEVEL}"
    --workers
    "${WORKERS}"
    --loop
    uvloop
    --http
    httptools
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

if [[ "$(id -u)" == "0" ]]; then
    # Ensure mounted volumes are writable for the app user.
    mkdir -p /app/logs /app/edi /app/data
    chown -R appuser:appuser /app/logs /app/edi /app/data || true
    # Drop privileges to appuser for runtime.
    uvicorn_cmd_str="$(printf '%q ' "${UVICORN_CMD[@]}")"
    exec su -s /bin/bash appuser -c "${uvicorn_cmd_str}"
fi

exec "${UVICORN_CMD[@]}"
