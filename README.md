# LPG Core Platform API

Minimal FastAPI Core Platform API for Business Central (On-Prem v18 / MS SQL Server) integration. This production-ready API centralizes purchasing operations with built-in idempotency, audit logging, and support for AI/OCR services.

## Features

- **Purchasing Operations**: PO line updates (date, price, quantity), receipts, and returns
- **Idempotency**: Built-in request deduplication using database-backed keys
- **Audit Trail**: Complete audit logging for all ERP-modifying operations
- **Type Safety**: Pydantic v2 validation with strict typing
- **ERP Integration**: Supports legacy functions and official API with canary deployment
- **AI/OCR Support**: Optional integration with OpenAI and OCR services
- **Production Ready**: Health checks, metrics, structured logging with Logfire

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Microsoft SQL Server (or use the included Docker container)
- ODBC Driver 17 for SQL Server

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd lpg-core-platform-api
```

2. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run with Docker Compose**
```bash
docker-compose up -d
```

4. **Run migrations**
```bash
docker-compose exec api sh -c "sqlcmd -S mssql -U sa -P 'YourStrong!Passw0rd' -i /app/app/sql/migrations.sql"
```

5. **Access the API**
- API: http://localhost:7003
- Documentation: http://localhost:7003/docs
- Health check: http://localhost:7003/healthz

### Enable HTTPS for Business Central webhooks

To terminate TLS directly in the API container with an existing certificate:

1. Place your certificate, private key, and optional CA bundle files in the local `cert/` directory (ignored by git).
2. Update `.env` with the in-container paths (matching the filenames you added):
   ```env
   TLS_CERT_FILE=/app/certs/your-domain.crt
   TLS_KEY_FILE=/app/certs/your-domain.key
   TLS_CA_BUNDLE=/app/certs/ca-bundle.crt  # optional, e.g. gd_bundle-g2.crt
   ```
3. Start the stack with Docker Compose:
   ```bash
   docker-compose up -d api
   ```
4. Business Central can now call `https://<your-host>:7003/api/v1/erp/webhooks/items` for validation and notifications.

The `entrypoint.sh` script enables TLS automatically when both `TLS_CERT_FILE` and `TLS_KEY_FILE` point to readable files. Leave the variables blank to run HTTP only.

### Local Development (without Docker)

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Set up database**
```sql
-- Run app/sql/migrations.sql in your MSSQL instance
```

3. **Run the application**
```bash
uvicorn app.main:app --reload --port 7003
```

## API Endpoints

### Health & Monitoring
- `GET /healthz` - Basic health check
- `GET /livez` - Liveness probe
- `GET /readyz` - Readiness probe with dependency checks
- `GET /metrics` - Application metrics

### ERP Operations

#### Update PO Line Promise Date
```bash
curl -X POST "http://localhost:7003/api/v1/erp/po/PO-001/lines/1/date" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-123" \
  -H "X-User-ID: john.doe" \
  -d '{
    "new_date": "2024-12-31",
    "reason": "Vendor delay notification"
  }'
```

#### Update PO Line Price
```bash
curl -X POST "http://localhost:7003/api/v1/erp/po/PO-001/lines/1/price" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-124" \
  -d '{
    "new_price": 29.99,
    "reason": "Negotiated discount"
  }'
```

#### Update PO Line Quantity
```bash
curl -X POST "http://localhost:7003/api/v1/erp/po/PO-001/lines/1/quantity" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-125" \
  -d '{
    "new_quantity": 150,
    "reason": "Increased demand"
  }'
```

#### Create Receipt
```bash
curl -X POST "http://localhost:7003/api/v1/erp/po/PO-001/receipts" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-126" \
  -d '{
    "po_id": "PO-001",
    "lines": [
      {
        "line_no": 1,
        "quantity": 100,
        "location_code": "MAIN"
      }
    ],
    "receipt_date": "2024-01-15"
  }'
```

#### Update Item Fields
```bash
curl -X POST "http://localhost:7003/api/v1/erp/items/ITEM-001/update" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: john.doe" \
  -d '{
    "updates": [
      {"field": "Description", "current_value": "Old name", "new_value": "New name"},
      {"field": "Unit_Cost", "new_value": 42.5}
    ]
  }'
```

#### Create Purchased Item (template 000)
```bash
curl -X POST "http://localhost:7003/api/v1/erp/items/purchased" \
  -H "Content-Type: application/json" \
  -d '{"item_no": "ITEM-NEW"}'
```

#### Create Manufactured Item (template 00000)
```bash
curl -X POST "http://localhost:7003/api/v1/erp/items/manufactured" \
  -H "Content-Type: application/json" \
  -d '{"item_no": "ITEM-MFG"}'
```

## Configuration

### Environment Variables

Key configuration options (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_DSN` | MSSQL connection string | Required |
| `ERP_MODE` | Integration mode: legacy/official/canary | legacy |
| `LOGFIRE_API_KEY` | Logfire observability key | Optional |
| `OPENAI_API_KEY` | OpenAI API key for AI features | Optional |
| `ENABLE_SCHEDULER` | Enable background job scheduler | false |

### ERP Mode Migration

The API supports three ERP integration modes:

1. **Legacy** (default): Uses existing Python functions
2. **Official**: Uses Business Central official API
3. **Canary**: Gradual rollout with percentage-based routing

To migrate from legacy to official API:
```bash
# Start with canary mode
ERP_MODE=canary
CANARY_PERCENT=10  # 10% traffic to new API

# Gradually increase
CANARY_PERCENT=50  # 50% traffic

# Full migration
ERP_MODE=official
```

## Architecture

```
app/
├── main.py               # FastAPI application initialization
├── settings.py           # Configuration management
├── db.py                 # Database connection pooling
├── errors.py             # Exception handling
├── deps.py               # Dependency injection
├── audit.py              # Audit logging & idempotency
├── domain/
│   ├── dtos.py          # Pydantic models
│   └── purchasing_service.py  # Business logic
├── adapters/
│   ├── erp_client.py    # ERP integration
│   ├── ocr_client.py    # OCR service
│   └── ai_client.py     # AI services
├── routers/
│   ├── health.py        # Health endpoints
│   └── purchasing.py    # Purchasing API
└── sql/
    └── migrations.sql   # Database schema
```

## Testing

### Run Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_update_poline_date.py

# With coverage
pytest --cov=app --cov-report=html
```

### Test Categories
- Unit tests: Business logic validation
- Integration tests: Database and ERP interaction
- API tests: Endpoint behavior and validation

## Production Deployment

### Docker Deployment
```bash
# Build production image
docker build -t lpg-core-api:latest .

# Run with production settings
docker run -d \
  --name lpg-api \
  -p 7003:7003 \
  -e ENVIRONMENT=production \
  -e DB_DSN="your-production-dsn" \
  -e LOGFIRE_API_KEY="your-key" \
  lpg-core-api:latest
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lpg-core-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: lpg-core-api:latest
        ports:
        - containerPort: 7003
        livenessProbe:
          httpGet:
            path: /livez
            port: 7003
        readinessProbe:
          httpGet:
            path: /readyz
            port: 7003
```

## Monitoring

### Logfire Integration
The API includes comprehensive Logfire instrumentation for:
- Request tracing
- Performance monitoring
- Error tracking
- Business metrics

### Health Checks
- `/healthz`: Basic health (always returns 200 if running)
- `/livez`: Liveness check for container orchestration
- `/readyz`: Readiness check with dependency validation

## Security

### Best Practices
- Never commit `.env` files or secrets
- Use strong passwords for database connections
- Enable TLS/SSL in production
- Implement proper authentication (not included in minimal version)
- Regular security updates for dependencies

### Idempotency
All write operations support idempotency via the `Idempotency-Key` header:
```bash
-H "Idempotency-Key: unique-request-id"
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify MSSQL is running: `docker-compose ps`
   - Check connection string in `.env`
   - Ensure ODBC Driver 17 is installed

2. **ERP Operations Failing**
   - Check `ERP_MODE` setting
   - Verify ERP_BASE_URL for official mode
   - Review logs: `docker-compose logs api`

3. **Idempotency Key Conflicts**
   - Keys are unique per operation
   - TTL is 24 hours by default
   - Check `IDEMPOTENCY_TTL_HOURS` setting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Your License Here]

## Working Agreement (Minimal)

- No direct pushes to `main` (open a PR).
- Write the adapter interface in `app/ports.py` FIRST.
- Services depend on Protocols, not concrete adapters.
- If you call a new adapter method, add it to the Protocol and implement it in the adapter; CI will fail if you forget.
- Run locally:
  ```bash
  pip install -r requirements.txt -r requirements-dev.txt
  mypy app
  pytest
  ```
- CI must be green (mypy + pytest) before merge.
- Deploy is automatic on merge to main (Docker image to GHCR + Portainer webhook).

## Support

For issues and questions:
- GitHub Issues: [repository-issues-url]
- Documentation: http://localhost:7003/docs (when running)
