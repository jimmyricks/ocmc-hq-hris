# API Layer

**Clean Architecture Position:** Outermost layer — the HTTP boundary.

The API layer translates HTTP requests into application service calls and application results back into HTTP responses. It knows about FastAPI, Pydantic schemas, and HTTP status codes. It must **not** contain business logic.

---

## Contents

```
api/
├── dependencies.py         # All FastAPI Depends() factories (single source of truth for DI)
├── router.py               # Aggregates all route groups
├── schemas/                # Pydantic request/response models
│   ├── base.py             # ActionRequest, ActionResponse, WorkflowRequest, ListResponse
│   ├── role.py             # RoleCreate, RoleUpdate
│   └── user.py             # UserCreate, UserUpdate
├── entries/                # Generic entity CRUD kernel (12 routes — handle all entities)
│   ├── entity_crud.py      # POST create, PUT update, DELETE, bulk delete
│   ├── entity_list.py      # GET list (with filters, sort, pagination), GET detail
│   ├── entity_workflow.py  # POST workflow action, GET workflow progress
│   ├── entity_actions.py   # POST server action
│   ├── entity_audit.py     # GET audit trail
│   ├── entity_print.py     # GET print preview, GET print PDF
│   ├── entity_options.py   # GET link field options (dropdowns)
│   ├── entity_prefill.py   # GET auto-fill values for new forms
│   ├── entity_children.py  # GET child table records, POST bulk save children
│   ├── entity_tree.py      # GET hierarchical tree
│   ├── entity_fetch_from.py # GET fetch-from field values
│   └── entity_attachments.py # POST upload, GET download, DELETE
├── features/               # Product feature endpoints
│   ├── search.py           # Global full-text search
│   ├── comments.py         # Entity comments
│   ├── favorites.py        # User favorites
│   ├── tags.py             # Entity tags
│   ├── timeline.py         # Activity timeline
│   ├── stock_count.py      # Inventory stock count
│   ├── diagram.py          # Entity relationship diagrams
│   ├── reports.py          # Reporting system
│   ├── operational_dashboard.py  # KPI dashboard
│   ├── pm_calendar/        # Preventive maintenance calendar
│   └── notifications/      # Notification inbox
├── system/                 # Infrastructure / admin endpoints
│   ├── auth.py             # POST /login, POST /logout
│   ├── profile.py          # GET /me, PUT /me, POST /change-password
│   ├── meta.py             # GET accessible entities, POST /meta/reload
│   ├── workflow.py         # Workflow CRUD (admin)
│   ├── health.py           # GET /health
│   ├── version.py          # GET /version
│   ├── audit_log.py        # GET audit log
│   ├── attachments.py      # System-level attachment handling
│   ├── feature_flags.py    # GET feature flag states
│   ├── import_export.py    # POST import, GET export
│   ├── setup.py            # POST first-run setup
│   ├── branding_settings.py # GET/PUT branding
│   ├── test_scheduler.py   # Manual scheduler triggers (dev/test)
│   └── admin/
│       ├── users.py        # User CRUD
│       ├── roles.py        # Role CRUD
│       ├── permissions.py  # Permission matrix
│       ├── api_keys.py     # API key management
│       ├── sessions.py     # Active session management
│       └── ordering.py     # Module / entity ordering
└── services/               # Backward-compat shims (re-exports to features/)
    ├── email.py
    └── notifications.py
```

---

## Dependency Injection (`dependencies.py`)

This file is the **single wiring point** for the entire application. Every route receives services through `Depends()` — never via direct instantiation.

```python
# api/dependencies.py

async def get_entity_service(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> EntityService:
    entity_repo = EntityRepository(db)
    rbac = RBACAppService(AuthRepository(db), permission_cache)
    return EntityService(entity_repo, rbac)
```

**Using a service in a route:**

```python
from app.api.dependencies import get_entity_service
from app.application.services.entity_service import EntityService

@router.get("/entity/{entity_name}/{record_id}")
async def get_detail(
    entity_name: str,
    record_id: str,
    svc: EntityService = Depends(get_entity_service),
    current_user: CurrentUser = Depends(get_current_user_from_token),
):
    return await svc.get_detail(entity_name, record_id, user=current_user)
```

---

## Router Groups (`router.py`)

Routes are grouped by concern and assembled in `router.py`:

| Group     | Prefix          | Description                                    |
| --------- | --------------- | ---------------------------------------------- |
| `ENTRY`   | `/api/entity`   | Generic CRUD kernel — handles all entities     |
| `SYSTEM`  | `/api`          | Auth, meta, workflow, admin, health            |
| `SERVICE` | `/api`          | Backward-compat shims                          |
| `APP`     | `/api`          | Cross-domain (dashboard, stock-count, reports) |
| `FEATURE` | `/api/features` | Product features (search, PM calendar, etc.)   |

---

## Generic Entity CRUD Kernel (`entries/`)

The 12 files in `entries/` handle all entity operations generically. The `entity_name` path parameter determines which entity is being operated on — no per-entity route code is needed.

### Key routes

```
GET  /api/entity/{entity_name}                  → paginated list
GET  /api/entity/{entity_name}/{record_id}       → single record detail
POST /api/entity/{entity_name}                   → create
PUT  /api/entity/{entity_name}/{record_id}       → update
DELETE /api/entity/{entity_name}/{record_id}     → delete
POST /api/entity/{entity_name}/{record_id}/workflow → workflow action
GET  /api/entity/{entity_name}/options           → link field dropdown options
POST /api/entity/{entity_name}/{record_id}/action → server action
GET  /api/entity/{entity_name}/{record_id}/print → print preview data
```

---

## Schemas (`schemas/`)

Pydantic models for HTTP request bodies and response shapes. Canonical definitions live here; `app/schemas/` are re-export shims for legacy compatibility.

```python
from app.api.schemas.base import ActionRequest, WorkflowRequest

class ActionRequest(BaseModel):
    action: str
    data: dict = {}

class WorkflowRequest(BaseModel):
    action: str
    comment: str | None = None
```

---

## Writing a New Route

1. **Create the file** in the appropriate subfolder (`entries/`, `features/`, or `system/`)
2. **Use `Depends()`** for all services — never instantiate services in route handlers
3. **Keep route handlers thin** — validate input, call one service method, return the result
4. **Register the route** in `router.py` in the correct group

```python
# api/features/my_feature.py
"""
API Layer: My Feature
Clean Architecture Layer: API
Responsibility: HTTP endpoints for my feature. Delegates to MyFeatureService.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user_from_token

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("/")
async def list_my_things(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_from_token),
):
    # Thin handler — delegate to service
    svc = MyFeatureService(db)
    return await svc.list_things(user=current_user)
```

Then in `router.py`:

```python
from app.api.features.my_feature import router as my_feature_router

APP_ROUTE_MODULES = [
    ...,
    ("app.api.features.my_feature", "/api"),
]
```

---

## Authentication

All protected routes use `get_current_user_from_token`:

```python
from app.core.security import CurrentUser, get_current_user_from_token

@router.post("/my-endpoint")
async def protected(current_user: CurrentUser = Depends(get_current_user_from_token)):
    if not current_user.is_superadmin:
        raise ForbiddenError("Superadmin only")
```

For admin-only endpoints, `current_user.role == "SystemManager"` or `current_user.is_superadmin`.

---

## Rules for This Layer

| Rule                                        | Detail                                                                            |
| ------------------------------------------- | --------------------------------------------------------------------------------- |
| **No business logic in route handlers**     | Handlers call one service method and return; never write `if/else` business rules |
| **No direct DB queries**                    | Always call a service; never use `db.execute(select(...))` in route files         |
| **All DI via `dependencies.py`**            | Never import and call infrastructure classes from routes                          |
| **Thin handlers**                           | A route handler should be ≤ 10 lines                                              |
| **Schemas own validation**                  | Use Pydantic models for all request body validation                               |
| **Error handling via `@handle_api_errors`** | Use the decorator; do not write try/except in handlers                            |
