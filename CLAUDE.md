# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Docker Compose Operations
```bash
# Start development stack (using existing SQL Server)
docker-compose up -d

# Rebuild and restart with fresh code (IMPORTANT: prevents cached code issues)
docker-compose down && docker image rm -f lpg-core-platform-api-api && docker-compose build --no-cache api && docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Verify fresh code is deployed inside container
docker exec -it lpg-core-platform-api sh -c "cat /app/app/main.py | grep -A5 'your-fix'"
```

### Database Operations
```bash
# Run migrations (requires running container)
docker-compose exec api sh -c "sqlcmd -S mssql -U sa -P 'YourStrong!Passw0rd' -i /app/app/sql/migrations.sql"
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_update_poline_date.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run unit tests only (skip slow/integration)
pytest -m "not slow"
```

### Code Quality
```bash
# Type checking
mypy app

# Linting and formatting (via pre-commit)
pre-commit run --all-files

# Individual tools
black app tests --line-length=100
ruff check app tests --fix
```

## Architecture Overview

### Hexagonal Architecture
The codebase follows hexagonal/ports-and-adapters architecture:

1. **Domain Layer** (`app/domain/`)
   - `purchasing_service.py`: Core business logic, orchestrates operations
   - `dtos.py`: Pydantic models for data validation and transfer
   - Business rules enforced here (e.g., date validation, quantity checks)

2. **Ports** (`app/ports.py`)
   - Protocol definitions that adapters must implement
   - Services depend on protocols, not concrete implementations
   - **CRITICAL**: Always define methods in protocol BEFORE using them

3. **Adapters** (`app/adapters/`)
   - `erp_client.py`: ERP integration (supports legacy/official/canary modes)
   - `ai_client.py`: OpenAI integration for PO analysis
   - `ocr_client.py`: OCR service integration
   - All adapters implement protocols from `ports.py`

4. **API Layer** (`app/routers/`)
   - `purchasing.py`: FastAPI endpoints for purchasing operations
   - `health.py`: Health check endpoints (/healthz, /livez, /readyz)

5. **Infrastructure**
   - `db.py`: Database connection pooling with SQLAlchemy
   - `audit.py`: Idempotency and audit logging with context managers
   - `settings.py`: Pydantic-based configuration management

### Key Patterns

1. **Idempotency**: All write operations support idempotency via `Idempotency-Key` header
   - Stored in database with TTL
   - Handled via `audit.py` functions

2. **Audit Logging**: Complete audit trail using `AuditContext` context manager
   - Automatic logging of all ERP-modifying operations
   - Tracks actor, changes, and reasons

3. **ERP Mode Migration**: Three integration modes for gradual migration:
   - `legacy`: Uses existing Python functions
   - `official`: Uses Business Central official API  
   - `canary`: Percentage-based routing between legacy and official

4. **Logfire Integration**: Comprehensive observability with spans
   - Use f-strings: `logfire.info(f'Message {variable}')`
   - Group related logs: `with logfire.span('operation_name'):`

## Important Conventions

1. **Never commit mock data** - Always use real data (conversation_id, PO numbers, etc.)

2. **Docker deployment verification** - Always check fresh code is deployed:
   ```bash
   docker exec -it lpg-core-platform-api sh -c "cat /app/app/[file] | grep [your-change]"
   ```

3. **Error handling** - All warnings/errors affect the end result and must be resolved

4. **Protocol-first development**:
   - Write adapter interface in `app/ports.py` FIRST
   - Then implement in adapter
   - MyPy will catch if methods are missing

5. **Testing approach**:
   - Check pytest markers in `pyproject.toml`
   - Integration tests marked with `@pytest.mark.integration`
   - Slow tests marked with `@pytest.mark.slow`

## API Endpoints

### Core ERP Operations
- `POST /api/v1/erp/po/{po_id}/lines/{line_no}/date` - Update promise date
- `POST /api/v1/erp/po/{po_id}/lines/{line_no}/price` - Update unit price
- `POST /api/v1/erp/po/{po_id}/lines/{line_no}/quantity` - Update quantity
- `POST /api/v1/erp/po/{po_id}/receipts` - Create goods receipt
- `POST /api/v1/erp/items/{item_id}/update` - Update item fields with concurrency checks
- `POST /api/v1/erp/items/purchased` - Create purchased item from template 000
- `POST /api/v1/erp/items/manufactured` - Create manufactured item from template 00000

### Health & Monitoring
- `GET /healthz` - Basic health check
- `GET /livez` - Liveness probe
- `GET /readyz` - Readiness with dependency checks
- `GET /metrics` - Application metrics

## Environment Configuration

Key environment variables (see `.env.example`):
- `DB_DSN`: MSSQL connection string (required)
- `ERP_MODE`: Integration mode (legacy/official/canary)
- `LOGFIRE_API_KEY`: Logfire observability
- `OPENAI_MODEL`: Use `gpt-5-2025-08-07` for best results
- `ENABLE_SCHEDULER`: Background job scheduler
- `IDEMPOTENCY_TTL_HOURS`: Idempotency key TTL (default: 24)

## Database Schema

Audit and idempotency tables are created via `app/sql/migrations.sql`:
- `audit_log`: Complete audit trail of all operations
- `idempotency_keys`: Request deduplication storage

## API Structure Rules

**CRITICAL**: Follow the API_STRUCTURE.md document for ALL endpoint implementations. Key rules:

1. **URL Structure**: `/api/v1/{domain}/{resource}/{id}/{sub-resource}/{action}`
   - Use kebab-case: `purchase-orders` NOT `purchaseOrders` or `purchase_orders`
   - Always plural: `orders` NOT `order`
   - Actions as sub-paths: `/actions/approve` NOT `/approve`

2. **File Organization**:
   ```
   app/api/v1/{domain}/{resource}.py  # Endpoints
   app/domain/{domain}/{resource}_service.py  # Business logic
   app/adapters/{domain}/{system}_client.py  # External integrations
   ```

3. **Response Structure**: ALWAYS use consistent JSON structure:
   ```json
   {
     "data": {...},
     "meta": {"timestamp": "...", "version": "1.0"},
     "links": {...}  // For collections
   }
   ```

4. **Current Mock Endpoints**: Legacy `/api/v1/purchasing/po/...` routes have been moved under `/api/v1/erp/...`.
   - Keep any new work under `/api/v1/erp/purchase-orders/...`
   - Refer to API_STRUCTURE.md Migration Strategy section for naming guidance

5. **Implementation Checklist**: Before creating ANY endpoint, verify it follows ALL rules in API_STRUCTURE.md Review Checklist

## Common Issues & Solutions

1. **Cached Docker images**: Always remove image before rebuild:
   ```bash
   docker image rm -f lpg-core-platform-api-api
   ```

2. **Database connection**: Verify MSSQL is accessible and DSN is correct

3. **Missing protocol methods**: Add to `ports.py` before implementing in adapter

4. **Logfire not initializing**: Check `LOGFIRE_API_KEY` is set correctly

5. **API Structure violations**: Check endpoint against API_STRUCTURE.md before implementation
