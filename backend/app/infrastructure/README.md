# Infrastructure Layer

**Clean Architecture Position:** Layer 3 — External adapters and framework wiring.

The infrastructure layer is where the application touches the outside world: databases, email servers, file systems, caches, schedulers, and third-party libraries. Every class here implements a domain protocol or provides a technical capability consumed by the application layer.

**Import rule:** Infrastructure may import from `domain/` and `core/`. It must **never** be imported by `application/` directly — only wired via `api/dependencies.py`.

> **Exception:** Print assemblers import `application/services/documents/print_formatters.py` and `print_resolver.py`. This is intentional — assemblers consume application formatting logic but remain infrastructure because they deal with data assembly, not business rules.

---

## Contents

```
infrastructure/
├── auth/
│   ├── jwt_service.py          # JWT creation and decoding (python-jose)
│   └── password_service.py     # bcrypt password hashing/verification
├── cache/
│   ├── ttl_cache.py            # In-memory TTL cache (singletons: query_cache, meta_cache)
│   └── permission_cache.py     # Role-permission cache with TTL (singleton: permission_cache)
├── database/
│   ├── connection.py           # Re-exports engine, session, Base from core
│   ├── unit_of_work.py         # SQLAlchemyUnitOfWork (async transaction scope)
│   └── repositories/
│       ├── entity_repository.py              # Generic CRUD for all entities
│       ├── auth_repository.py                # User, Role, Permission queries
│       ├── workflow_repository.py            # Workflow state machine queries
│       ├── document_repository.py            # Flexible field-selection queries
│       ├── dashboard_repository.py           # Aggregation / raw SQL metrics
│       ├── naming_repository.py              # Auto-increment series (WO-001, PR-002…)
│       ├── fetch_from_repository.py          # Partial field extraction
│       ├── tree.py                           # Hierarchical tree queries
│       └── notification_subscription_repository.py  # Notification preferences
├── email/
│   ├── smtp_service.py         # Async SMTP via aiosmtplib (implements EmailServiceProtocol)
│   ├── template_renderer.py    # Jinja2 template rendering (implements EmailTemplateRendererProtocol)
│   └── notification_factory.py # Builds EmailNotificationDispatcher with all wiring
├── events/
│   └── domain_event_bus.py     # In-process pub/sub (singleton: domain_event_bus)
├── logging/
│   ├── email_logger.py         # Logs email send attempts to email_log table
│   └── job_logger.py           # Logs scheduled job runs to scheduled_job_log table
├── metadata/
│   ├── adapters.py             # Re-export shim for backward compatibility
│   ├── reader.py               # JsonMetadataReader — reads entity JSON from disk
│   ├── writer.py               # JsonMetadataWriter — writes + backs up entity JSON
│   ├── validator.py            # MetadataValidator — structural validation
│   ├── model_generator.py      # ModelGeneratorService — generates SQLAlchemy model code
│   ├── migration_service.py    # MigrationService — wraps Alembic (generate/apply/rollback)
│   └── integrity.py            # Startup integrity check (metadata ↔ model consistency)
├── print/
│   ├── registry.py             # Print assembler registry (OCP pattern)
│   └── assemblers/
│       ├── loader.py           # Discovers and registers assemblers
│       ├── work_order.py       # WorkOrderAssembler (labor, parts, equipment, activities)
│       ├── incident.py         # IncidentAssembler
│       ├── purchase_request.py # PurchaseRequestAssembler
│       └── purchase_order.py   # PurchaseOrderAssembler
├── realtime/                   # (directory kept for future Socket.IO infrastructure)
├── rate_limit.py               # slowapi Limiter singleton
├── scheduler/
│   └── scheduler_adapter.py    # APScheduler async wrapper (SchedulerAdapter)
├── settings/
│   └── branding_store.py       # JSON file-based branding (implements BrandingStoreProtocol)
└── storage/
    ├── __init__.py             # get_storage() factory (local or S3 based on env var)
    ├── base.py                 # StorageBackend Protocol, StoredFile dataclass
    ├── local_storage.py        # LocalStorageBackend (UPLOAD_DIR/<entity>/<record>/<uuid>.<ext>)
    └── s3_storage.py           # S3StorageBackend (AWS S3 with presigned URLs)
```

---

## Repositories

All database access must go through a repository. Repositories implement domain protocols, so application services depend on the protocol, not the SQLAlchemy class.

### Generic Entity Repository

Handles all metadata-driven entities. Models are registered dynamically at startup.

```python
from app.infrastructure.database.repositories.entity_repository import EntityRepository

repo = EntityRepository(db)
record = await repo.get_by_id("work_order", "WO-001")
records, total = await repo.get_list("work_order", filters={"status": "Open"}, page=1, page_size=20)
new_record = await repo.create("work_order", {"title": "Pump repair"}, user_id="1")
```

### Auth Repository

User, Role, and Permission queries with eager loading.

```python
from app.infrastructure.database.repositories.auth_repository import AuthRepository

repo = AuthRepository(db)
user = await repo.get_user_by_email("john@acme.com")
roles = await repo.get_all_roles()
perms = await repo.get_role_permissions("SystemManager")
```

### Workflow Repository

State machine queries. Reads from DB with JSON fallback.

```python
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository

repo = WorkflowRepository(db)
actions = await repo.get_available_actions("work_order", "Open", role="SystemManager")
is_valid = await repo.validate_transition("work_order", "Draft", "Submit")
```

---

## Email

Email is built in three layers:

| File                      | Role                                           |
| ------------------------- | ---------------------------------------------- |
| `smtp_service.py`         | Sends the email — knows about SMTP only        |
| `template_renderer.py`    | Renders Jinja2 HTML templates                  |
| `notification_factory.py` | Wires these into `EmailNotificationDispatcher` |

The factory is called from `api/dependencies.py` (request context) and from hooks/schedulers (non-request context) using a fresh DB session.

```python
# Non-request context (hooks, schedulers)
from app.infrastructure.email.notification_factory import build_email_notification_dispatcher

async with async_session_maker() as db:
    dispatcher = build_email_notification_dispatcher(db)
    await dispatcher.dispatch("work_order.created", record_id="WO-001", db=db)
```

---

## Metadata

The metadata layer handles the entity JSON definition lifecycle: read, validate, write, generate models, generate migrations.

```
JSON file → Reader → Validator → Writer (with backup)
                             ↓
                     ModelGenerator → .py model file
                             ↓
                     MigrationService → Alembic migration
```

Prefer using the Forge CLI (`python -m app.forge sync`) rather than calling these services directly.

---

## Storage

File storage is pluggable. `get_storage()` returns the correct backend based on `STORAGE_BACKEND` env var.

```python
from app.infrastructure.storage import get_storage

storage = get_storage()
stored = await storage.save(content=file_bytes, filename="photo.jpg", entity="asset", record_id="A-001")
url = stored.url
```

Switch to S3 by setting `STORAGE_BACKEND=s3` with the appropriate AWS env vars.

---

## Cache

Two in-memory caches are available as module-level singletons:

| Singleton          | Purpose                       | TTL           |
| ------------------ | ----------------------------- | ------------- |
| `query_cache`      | General query results         | Configurable  |
| `meta_cache`       | Entity metadata               | Long (stable) |
| `permission_cache` | Role → entity → action matrix | 5 minutes     |

```python
from app.infrastructure.cache.ttl_cache import query_cache
from app.infrastructure.cache.permission_cache import permission_cache

# Cache a result
query_cache.set("work_order:list:Open", result, ttl=60)
cached = query_cache.get("work_order:list:Open")

# Invalidate permission cache after role change
permission_cache.delete(f"role:{role_name}")
```

---

## Print Assemblers

Print assemblers collect all data needed for a print template. They are registered in `registry.py` and looked up by entity name.

```python
from app.infrastructure.print.registry import get_assembler

assembler = get_assembler("work_order")
data = await assembler.assemble(record_id="WO-001", db=db)
```

Assemblers use `application/services/documents/print_resolver.py` for link title resolution and `application/services/documents/print_formatters.py` for display formatting.

---

## Rules for This Layer

| Rule                                      | Detail                                                                                                |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Implement domain protocols**            | Each repository/service should implement the corresponding `domain/protocols/` Protocol               |
| **No business logic in repositories**     | Repos query data; they do not make decisions about it                                                 |
| **No cross-repository calls**             | Repositories must not call each other                                                                 |
| **Factories live here**                   | DI wiring for infrastructure belongs in this layer (e.g., `notification_factory.py`)                  |
| **No direct imports from `application/`** | Except print assemblers using formatters/resolver (documented exception)                              |
| **Singletons are module-level**           | Cache and event bus singletons are fine at module level; do not use global state for stateful objects |
