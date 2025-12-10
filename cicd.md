 
🧠 EXECUTION PROMPT — Minimal CI/CD & Guardrails (GitHub, pytest, mypy, Docker, GHCR)

You are updating an existing FastAPI repo (single app) to add basic CI/CD and compile-time guardrails that prevent LLM-introduced breakage (e.g., calling adapter functions that don’t exist).

Goals
•	CI runs on PR and on push to main.
•	Run unit tests and a health smoke test.
•	Run mypy (types only; no lint/format tools).
•	On main, build Docker, push to GitHub Container Registry (GHCR), then hit an optional Portainer webhook to redeploy.
•	Enforce “no missing functions” by using Protocol types for adapters and mypy checks in CI.

Changes to implement

1) Dependencies (dev)

Create requirements-dev.txt (or add to your existing dev file):
pytest
mypy
types-requests
httpx
Ensure requirements.txt contains runtime deps (fastapi, uvicorn, sqlalchemy, pyodbc, pydantic, httpx, tenacity, logfire, etc.).

2) mypy config

Add mypy.ini at repo root:
[mypy]
python_version = 3.11
strict = True
warn_unused_ignores = True
warn_redundant_casts = True
warn_return_any = True
no_implicit_optional = True
disallow_any_generics = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
ignore_missing_imports = False

[mypy-app.*]
implicit_reexport = False
3) Adapter Protocols (to catch “function doesn’t exist”)

Create app/ports.py:
from typing import Protocol
from datetime import date
from typing import Any, Dict

class ERPClientProtocol(Protocol):
    def get_poline(self, po_id: str, line_no: int) -> Dict[str, Any]: ...
    def update_poline_date(self, po_id: str, line_no: int, new_date: date) -> Dict[str, Any]: ...
Update app/adapters/erp_client.py to implement ERPClientProtocol:
from datetime import date
from typing import Any, Dict
from app.ports import ERPClientProtocol

class ERPClient(ERPClientProtocol):
    def __init__(self, legacy_impl):  # keep minimal
        self.legacy = legacy_impl

    def get_poline(self, po_id: str, line_no: int) -> Dict[str, Any]:
        return self.legacy.get_poline(po_id, line_no)

    def update_poline_date(self, po_id: str, line_no: int, new_date: date) -> Dict[str, Any]:
        return self.legacy.update_poline_date(po_id, line_no, new_date)
Update service constructor or wiring so the service accepts ERPClientProtocol, not a concrete class:
# app/domain/purchasing_service.py (example pattern)
from app.ports import ERPClientProtocol
from datetime import date

class PurchasingService:
    def __init__(self, erp: ERPClientProtocol):
        self.erp = erp

    def update_poline_date(self, po_id: str, line_no: int, new_date: date, *, reason: str, idem: str):
        # call self.erp.update_poline_date(...) etc.
        ...
If an LLM adds erp.update_price(...) but the Protocol doesn’t have it, mypy fails CI.

4) Tests

Add tests/test_health.py:
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_health():
    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
(Keep your existing business tests. This one is the bare smoke.)

5) Simple version stamp (for images)

Create scripts/version.sh:
#!/usr/bin/env bash
set -euo pipefail
SHA=$(git rev-parse --short HEAD)
DATE=$(date -u +%Y%m%d%H%M%S)
echo "${DATE}-${SHA}"
Make it executable: chmod +x scripts/version.sh

6) Dockerfile (confirm minimal)

Ensure your Dockerfile builds the app and exposes 8000. Example:
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    unixodbc unixodbc-dev curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
7) GitHub Actions — 
CI

Create .github/workflows/ci.yml:
name: CI

on:
  pull_request:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Type check (mypy)
        run: mypy app

      - name: Unit tests (pytest)
        env:
          # if your app imports MSSQL at import-time, mock or guard it
          ENV: test
        run: pytest -q
8) GitHub Actions — CD (Continuous Deployment)

Create .github/workflows/cd.yml for production deployment:

```yaml
name: CD

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: self-hosted
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: actions/setup-buildx-action@v3

    - name: Log in to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_HUB_USERNAME }}
        password: ${{ secrets.DOCKER_HUB_TOKEN }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64
        push: true
        tags: ${{ secrets.DOCKER_HUB_USERNAME }}/lpg-core-platform-api:latest

    - name: Deploy to production server
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.PRODUCTION_HOST }}
        username: ${{ secrets.PRODUCTION_USER }}
        key: ${{ secrets.PRODUCTION_SSH_KEY }}
        script: |
          cd /opt/lpg-core-platform-api
          docker pull ${{ secrets.DOCKER_HUB_USERNAME }}/lpg-core-platform-api:latest
          docker-compose -f docker-compose.prod.yml down
          docker-compose -f docker-compose.prod.yml up -d
          docker image prune -f
```

**GitHub Secrets: None Required**
Since you're using a self-hosted runner on your Docker server, no GitHub secrets are needed. The runner builds and deploys directly on the host system.

9) Branch protection (enforced by you in GitHub UI)
•	Protect main:
o	Require status checks to pass: CI (mypy + pytest)
o	Dismiss stale approvals on new commits (optional)
o	Require PR (recommended)
This is how you “respect the system”: you simply can’t merge unless CI passes.

10) README section — “How to work in this repo”

Append to README.md:
## Working Agreement (Minimal)
- No direct pushes to `main` (open a PR).
- Write the adapter interface in `app/ports.py` FIRST.
- Services depend on Protocols, not concrete adapters.
- If you call a new adapter method, add it to the Protocol and implement it in the adapter; CI will fail if you forget.
- Run locally:
  pip install -r requirements.txt -r requirements-dev.txt
  mypy app
  pytest
- CI must be green (mypy + pytest) before merge.
- Deploy is automatic on merge to main (Docker image to GHCR + Portainer webhook).
Notes
•	We purposely avoid lint/format to stay minimal. Only mypy for “does this function exist with the right signature?”
•	If imports try to connect to MSSQL at import time, guard with if os.getenv("ENV") == "test": or use dependency injection so tests don’t need the DB.
•	The /api/health route should not hit external systems; it must always return quickly for the smoke test.
 
End of Execution Prompt
 


