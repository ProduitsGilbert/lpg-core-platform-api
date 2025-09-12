#!/bin/bash
cd /app
export PYTHONPATH=/app:$PYTHONPATH
exec /opt/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 7003 --log-level info