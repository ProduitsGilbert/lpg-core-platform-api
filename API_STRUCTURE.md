# API Structure & Naming Conventions

## Overview
This document defines the strict API structure and naming conventions for the LPG Core Platform API. This is a multi-domain enterprise platform API serving various departments with integrations to ERP, AI services, document processing, and data systems.

## Core Principles

1. **Resource-Based Design**: Use nouns for resources, not verbs
2. **Action-Based Operations**: Use POST with action suffix for non-CRUD operations
3. **Consistent Pluralization**: Always use plural for collections
4. **Domain Segregation**: Clear separation between business domains
5. **Version Strategy**: URL versioning with `/api/v1` prefix
6. **Predictable Responses**: Consistent response structure across all endpoints

## URL Structure

```
https://api.lpg.com/api/v1/{domain}/{resource}/{resource-id}/{sub-resource}/{action}
```

### Components:
- `api/v1`: API version prefix (REQUIRED)
- `{domain}`: Business domain (e.g., erp, ai, documents, data)
- `{resource}`: Plural resource name (e.g., purchase-orders, invoices)
- `{resource-id}`: Resource identifier
- `{sub-resource}`: Optional nested resource
- `{action}`: POST-based action for operations beyond CRUD

## Domain Structure

### 1. ERP Domain (`/api/v1/erp`)
Business Central and SQL Server integrations

```
/api/v1/erp/purchase-orders                    # GET, POST
/api/v1/erp/purchase-orders/{id}              # GET, PUT, DELETE
/api/v1/erp/purchase-orders/{id}/lines        # GET, POST
/api/v1/erp/purchase-orders/{id}/lines/{line_id}  # GET, PUT, DELETE
/api/v1/erp/purchase-orders/{id}/actions/approve  # POST
/api/v1/erp/purchase-orders/{id}/actions/receive  # POST

/api/v1/erp/sales-orders
/api/v1/erp/invoices
/api/v1/erp/vendors
/api/v1/erp/customers
/api/v1/erp/items
/api/v1/erp/items/{item_id}/tariff (`?include_details=true` to return the full materials table)
/api/v1/erp/inventory
/api/v1/erp/bc/posted-sales-invoice-headers
/api/v1/erp/bc/purchase-order-headers
/api/v1/erp/bc/purchase-order-lines
/api/v1/erp/bc/vendors
/api/v1/erp/bc/items
/api/v1/erp/bc/sales-order-headers
/api/v1/erp/bc/sales-order-lines
/api/v1/erp/bc/sales-quote-headers
/api/v1/erp/bc/sales-quote-lines
```

### 2. AI Domain (`/api/v1/ai`)
AI services including OpenAI, predictions, and agents

```
/api/v1/ai/typing-suggestions                   # POST
/api/v1/ai/deep-reasoning                       # POST
/api/v1/ai/standard-response                    # POST
/api/v1/ai/streaming-response                   # POST (SSE stream)
/api/v1/ai/sample-response                      # POST
/api/v1/ai/openrouter-response                  # POST (multi-model)

Allowed OpenRouter models: Grok Code Fast 1, Claude Sonnet 4.5, Gemini 2.5 Flash, MiniMax M2 (free), Gemini 2.5 Pro, Grok 4 Fast, Gemini 2.0 Flash, Claude Sonnet 4, Gemini 2.5 Flash Lite.

/api/v1/ai/ocr/documents                      # POST (upload)
/api/v1/ai/ocr/documents/{id}                 # GET results
/api/v1/ai/ocr/documents/{id}/actions/extract # POST

/api/v1/ai/predictions/demand                 # POST
/api/v1/ai/predictions/inventory              # POST
/api/v1/ai/predictions/{id}                   # GET

/api/v1/ai/agents                             # GET, POST
/api/v1/ai/agents/{id}/actions/trigger        # POST
/api/v1/ai/agents/{id}/conversations          # GET
/api/v1/ai/agents/{id}/conversations/{conv_id}/messages # POST

/api/v1/ai/analysis/purchase-orders           # POST
/api/v1/ai/analysis/documents                 # POST
```

### 3. Documents Domain (`/api/v1/documents`)
Document management and processing

```
/api/v1/documents/uploads                     # POST
/api/v1/documents/uploads/{id}                # GET, DELETE
/api/v1/documents/uploads/{id}/actions/process # POST
/api/v1/documents/uploads/{id}/metadata       # GET, PUT

/api/v1/documents/templates                   # GET, POST
/api/v1/documents/templates/{id}/actions/generate # POST
```

### 4. Communications Domain (`/api/v1/communications`)
Email and messaging integrations

```
/api/v1/communications/emails                 # GET, POST
/api/v1/communications/emails/{id}            # GET
/api/v1/communications/emails/{id}/actions/reply # POST
/api/v1/communications/emails/{id}/actions/forward # POST
/api/v1/communications/emails/{id}/attachments # GET

/api/v1/communications/notifications          # GET, POST
/api/v1/communications/notifications/{id}/actions/mark-read # POST
```

### 5. Data Domain (`/api/v1/data`)
Direct data access and queries

```
/api/v1/data/queries                          # POST (execute query)
/api/v1/data/queries/{id}/results             # GET
/api/v1/data/exports                          # POST
/api/v1/data/exports/{id}                     # GET status
/api/v1/data/exports/{id}/download            # GET file

/api/v1/data/reports/{report_type}            # GET
/api/v1/data/dashboards/{dashboard_id}        # GET
```

### 6. Workflows Domain (`/api/v1/workflows`)
Business process automation

```
/api/v1/workflows/processes                   # GET, POST
/api/v1/workflows/processes/{id}              # GET
/api/v1/workflows/processes/{id}/actions/start # POST
/api/v1/workflows/processes/{id}/actions/cancel # POST
/api/v1/workflows/processes/{id}/tasks        # GET
/api/v1/workflows/processes/{id}/tasks/{task_id}/actions/complete # POST
```

### 7. MRP Domain (`/api/v1/mrp`)
Advanced production planning utilities

```
/api/v1/mrp/production-orders                     # GET
/api/v1/mrp/production-orders/export              # GET (Excel)
```


## File Structure

```
app/
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── erp/
│       │   ├── __init__.py
│       │   ├── purchase_orders.py
│       │   ├── sales_orders.py
│       │   ├── invoices.py
│       │   ├── vendors.py
│       │   ├── customers.py
│       │   └── items.py
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── ocr.py
│       │   ├── predictions.py
│       │   ├── agents.py
│       │   └── analysis.py
│       ├── documents/
│       │   ├── __init__.py
│       │   ├── uploads.py
│       │   └── templates.py
│       ├── communications/
│       │   ├── __init__.py
│       │   ├── emails.py
│       │   └── notifications.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── queries.py
│       │   ├── exports.py
│       │   └── reports.py
│       └── workflows/
│           ├── __init__.py
│           └── processes.py
├── domain/
│   ├── erp/
│   │   ├── purchase_order_service.py
│   │   ├── sales_order_service.py
│   │   └── models.py
│   ├── ai/
│   │   ├── ocr_service.py
│   │   ├── prediction_service.py
│   │   └── models.py
│   └── [other domains...]
├── adapters/
│   ├── erp/
│   │   ├── business_central_client.py
│   │   └── sql_server_client.py
│   ├── ai/
│   │   ├── openai_client.py
│   │   └── ocr_client.py
│   └── [other adapters...]
└── infrastructure/
    ├── database/
    ├── cache/
    └── messaging/
```

## Naming Conventions

### URLs
- **Use kebab-case**: `purchase-orders`, not `purchaseOrders` or `purchase_orders`
- **Always plural for collections**: `orders`, not `order`
- **Use nouns**: `documents`, not `getDocuments`
- **Actions as sub-paths**: `/actions/approve`, not `/approve`

### Python Files & Functions
- **Snake_case for files**: `purchase_orders.py`
- **Snake_case for functions**: `get_purchase_order()`
- **PascalCase for classes**: `PurchaseOrderService`
- **Snake_case for variables**: `order_total`

### Request/Response Models
- **Suffix with purpose**:
  - `*Request`: Input models (e.g., `CreatePurchaseOrderRequest`)
  - `*Response`: Output models (e.g., `PurchaseOrderResponse`)
  - `*Command`: Service commands (e.g., `UpdatePriceCommand`)
  - `*Query`: Query models (e.g., `PurchaseOrderQuery`)
  - `*DTO`: Data transfer objects (e.g., `PurchaseOrderDTO`)

## HTTP Methods & Status Codes

### Method Usage
- **GET**: Retrieve resource(s)
- **POST**: Create resource OR perform action
- **PUT**: Full update of resource
- **PATCH**: Partial update of resource
- **DELETE**: Remove resource

### Standard Status Codes
- **200 OK**: Successful GET, PUT, PATCH
- **201 Created**: Successful POST creating resource
- **202 Accepted**: Async operation started
- **204 No Content**: Successful DELETE
- **400 Bad Request**: Invalid input
- **401 Unauthorized**: Missing/invalid auth
- **403 Forbidden**: No permission
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource conflict (e.g., duplicate)
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

## Response Structure

### Success Response
```json
{
  "data": {
    "id": "PO-2024-001",
    "type": "purchase-order",
    "attributes": {
      "vendor_id": "V-123",
      "total_amount": 15000.00,
      "currency": "USD",
      "status": "pending"
    },
    "relationships": {
      "lines": {
        "data": [
          {"type": "purchase-order-line", "id": "1"},
          {"type": "purchase-order-line", "id": "2"}
        ]
      }
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0"
  }
}
```

### Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed for the request",
    "details": [
      {
        "field": "amount",
        "message": "Amount must be greater than 0",
        "code": "MIN_VALUE"
      }
    ],
    "trace_id": "abc-123-def",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Collection Response
```json
{
  "data": [...],
  "meta": {
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_pages": 5,
      "total_items": 95
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "links": {
    "self": "/api/v1/erp/purchase-orders?page=1",
    "next": "/api/v1/erp/purchase-orders?page=2",
    "last": "/api/v1/erp/purchase-orders?page=5"
  }
}
```

## Query Parameters

### Standard Parameters
- **Pagination**: `?page=1&per_page=20`
- **Sorting**: `?sort=created_at:desc,amount:asc`
- **Filtering**: `?filter[status]=pending&filter[amount_gt]=1000`
- **Field selection**: `?fields=id,vendor_id,total_amount`
- **Relationships**: `?include=lines,vendor`
- **Date ranges**: `?date_from=2024-01-01&date_to=2024-01-31`

## Implementation Rules

### 1. Router Registration
Each domain must register its routers in a consistent manner:

```python
# app/api/v1/erp/__init__.py
from fastapi import APIRouter
from .purchase_orders import router as po_router
from .sales_orders import router as so_router

router = APIRouter(prefix="/erp", tags=["ERP"])
router.include_router(po_router)
router.include_router(so_router)
```

### 2. Endpoint Definition
```python
# app/api/v1/erp/purchase_orders.py
from fastapi import APIRouter, Depends, Query
from typing import Optional

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])

@router.get("")
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query(None),
    filter: Optional[dict] = Query(None)
):
    """List purchase orders with pagination and filtering"""
    pass

@router.post("/{po_id}/actions/approve")
async def approve_purchase_order(
    po_id: str,
    request: ApprovePurchaseOrderRequest
):
    """Approve a purchase order"""
    pass
```

### 3. Service Layer Pattern
Always use service layer for business logic:

```python
# app/domain/erp/purchase_order_service.py
class PurchaseOrderService:
    def __init__(self, erp_adapter: ERPAdapter):
        self.erp = erp_adapter
    
    async def list_orders(self, filters: dict) -> List[PurchaseOrderDTO]:
        """Business logic for listing orders"""
        pass
    
    async def approve_order(self, po_id: str, approver: str) -> PurchaseOrderDTO:
        """Business logic for approving order"""
        pass
```

## Migration Strategy

### Current Endpoint Analysis
The current endpoint `/api/v1/erp/po/{po_id}/lines/{line_no}/date` has issues:
1. Uses abbreviation "po" instead of full "purchase-orders"
2. Verb-like operation embedded in path
3. Inconsistent with REST principles

### Recommended Migration
```
OLD: POST /api/v1/erp/po/{po_id}/lines/{line_no}/date
NEW: PATCH /api/v1/erp/purchase-orders/{po_id}/lines/{line_id}
     Body: {"promise_date": "2024-12-31"}

OR for action-based:
NEW: POST /api/v1/erp/purchase-orders/{po_id}/lines/{line_id}/actions/update-date
     Body: {"new_date": "2024-12-31", "reason": "Vendor delay"}
```

## Versioning Strategy

### API Version Management
1. **Major versions in URL**: `/api/v1`, `/api/v2`
2. **Minor versions in headers**: `API-Version: 1.2`
3. **Deprecation policy**: 
   - Announce 6 months before
   - Support old version for 12 months
   - Return `Sunset` header with deprecation date

### Backward Compatibility
- Never remove fields from responses
- Mark deprecated fields clearly
- Use feature flags for gradual rollout
- Maintain old endpoints with redirect/proxy

## Security Considerations

### Authentication & Authorization
- Bearer token in header: `Authorization: Bearer <token>`
- API keys for service-to-service: `X-API-Key: <key>`
- Scoped permissions per endpoint

### Rate Limiting Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

### Audit Headers
```
X-Request-ID: unique-request-id
X-Trace-ID: distributed-trace-id
X-User-ID: authenticated-user
Idempotency-Key: client-generated-key
```

## Testing Requirements

### Endpoint Testing
1. Unit tests for each endpoint
2. Integration tests for workflows
3. Contract tests for external APIs
4. Load tests for critical paths

### Test Naming
```python
def test_list_purchase_orders_returns_paginated_results():
def test_approve_purchase_order_validates_permissions():
def test_update_line_quantity_checks_business_rules():
```

## Documentation Standards

### OpenAPI/Swagger
- Every endpoint must have OpenAPI docs
- Include request/response examples
- Document all error codes
- Specify rate limits

### Endpoint Documentation Template
```python
@router.post(
    "/{po_id}/actions/approve",
    response_model=PurchaseOrderResponse,
    status_code=200,
    summary="Approve a purchase order",
    description="""
    Approves a purchase order and triggers the approval workflow.
    
    Requirements:
    - User must have approval permissions
    - Order must be in 'pending' status
    - Order amount must be within approval limits
    """,
    responses={
        200: {"description": "Order approved successfully"},
        400: {"description": "Invalid request"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Order not found"},
        409: {"description": "Order not in approvable state"}
    }
)
```

## Performance Guidelines

### Response Time Targets
- Simple GET: < 200ms
- Complex queries: < 1s
- Async operations: Return 202 immediately
- Bulk operations: Use pagination or streaming

### Caching Strategy
- Cache-Control headers for GET requests
- ETag for resource versioning
- Use Redis for frequently accessed data

## Monitoring & Observability

### Required Metrics
- Request count by endpoint
- Response time percentiles (p50, p95, p99)
- Error rates by status code
- Business metrics (orders created, etc.)

### Logging Standards
```python
logfire.info(f"Purchase order created", 
    po_id=po_id,
    vendor_id=vendor_id,
    amount=amount,
    user_id=user_id
)
```

## Compliance & Governance

### Data Privacy
- PII must be encrypted at rest
- Sensitive fields excluded from logs
- GDPR-compliant data deletion

### Audit Trail
- All write operations logged
- Include user, timestamp, changes
- Immutable audit log storage

## Review Checklist

Before implementing any endpoint, verify:

- [ ] Follows URL structure convention
- [ ] Uses appropriate HTTP method
- [ ] Has consistent response structure
- [ ] Includes proper error handling
- [ ] Has comprehensive tests
- [ ] Documented in OpenAPI
- [ ] Implements authentication/authorization
- [ ] Includes audit logging
- [ ] Follows service layer pattern
- [ ] Uses proper status codes
- [ ] Supports idempotency (for POST/PUT)
- [ ] Has rate limiting configured
- [ ] Metrics and logging implemented
- [ ] Performance targets met
