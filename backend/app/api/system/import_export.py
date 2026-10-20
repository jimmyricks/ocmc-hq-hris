from __future__ import annotations

import io
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.import_export_service import ImportExportService
from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.application.services.access_control.row_scope_service import RowScopeService
from app.api.dependencies import get_rbac_service, get_row_scope_service, get_import_export_service
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.services.integrations import import_export as ie
from app.application.services.documents.link_title_service import build_link_titles_batch

router = APIRouter(prefix="/import-export", tags=["import-export"])


class CustomExportRequest(BaseModel):
    record_ids: Optional[list[str]] = None
    fields: Optional[list[str]] = None
    format: str = "xlsx"


@router.get("/{entity}/template")
async def download_template(
    entity: str,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="create",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    link_options = await ie.build_link_options(db, meta)
    content = ie.build_template(meta, link_options)
    filename = f"{entity}_import_template.xlsx"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{entity}/validate")
async def validate_import(
    entity: str,
    file: UploadFile = File(...),
    mode: str = Query("create", pattern="^(create|update)$"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
    import_export_service: ImportExportService = Depends(get_import_export_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    permission = "update" if mode == "update" else "create"
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action=permission,
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    headers, rows = ie.parse_upload(file)
    result = await import_export_service.validate_import(meta, headers, rows, mode=mode)
    return ActionResponse(
        status="success" if result.valid else "error",
        message="Validation complete",
        data={"valid": result.valid, "errors": result.errors, "rows": result.rows, "warnings": result.warnings},
    )


@router.post("/{entity}/validate/sheets")
async def validate_import_sheets(
    entity: str,
    sheets_url: str = Body(..., embed=True),
    mode: str = Query("create", pattern="^(create|update)$"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
    import_export_service: ImportExportService = Depends(get_import_export_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    permission = "update" if mode == "update" else "create"
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action=permission,
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    headers, rows = ie.parse_google_sheet(sheets_url)
    result = await import_export_service.validate_import(meta, headers, rows, mode=mode)
    return ActionResponse(
        status="success" if result.valid else "error",
        message="Validation complete",
        data={"valid": result.valid, "errors": result.errors, "rows": result.rows, "warnings": result.warnings},
    )


@router.post("/{entity}/execute")
async def execute_import(
    entity: str,
    file: UploadFile = File(...),
    mode: str = Query("create", pattern="^(create|update)$"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
    import_export_service: ImportExportService = Depends(get_import_export_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    permission = "update" if mode == "update" else "create"
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action=permission,
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    headers, rows = ie.parse_upload(file)
    validation = await import_export_service.validate_import(meta, headers, rows, mode=mode)
    if not validation.valid:
        return ActionResponse(status="error", message="Validation failed", data={"errors": validation.errors, "warnings": validation.warnings})

    result = await import_export_service.execute_import(
        meta, headers, rows, mode=mode, row_scope_service=row_scope_service, user=user
    )
    message = f"Updated {result.updated} records" if mode == "update" else f"Imported {result.count} records"
    if result.duplicates:
        message += f" (skipped {result.duplicates} duplicates)"
    if result.missing:
        message += f" ({result.missing} missing records skipped)"
    if getattr(result, "inaccessible", 0):
        message += f" ({result.inaccessible} inaccessible records skipped)"
    return ActionResponse(
        status="success",
        message=message,
        data={"count": result.count, "duplicates": result.duplicates, "updated": result.updated, "missing": result.missing, "inaccessible": getattr(result, "inaccessible", 0)},
    )


@router.post("/{entity}/execute/sheets")
async def execute_import_sheets(
    entity: str,
    sheets_url: str = Body(..., embed=True),
    mode: str = Query("create", pattern="^(create|update)$"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
    import_export_service: ImportExportService = Depends(get_import_export_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    permission = "update" if mode == "update" else "create"
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action=permission,
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    headers, rows = ie.parse_google_sheet(sheets_url)
    validation = await import_export_service.validate_import(meta, headers, rows, mode=mode)
    if not validation.valid:
        return ActionResponse(status="error", message="Validation failed", data={"errors": validation.errors, "warnings": validation.warnings})

    result = await import_export_service.execute_import(
        meta, headers, rows, mode=mode, row_scope_service=row_scope_service, user=user
    )
    message = f"Updated {result.updated} records" if mode == "update" else f"Imported {result.count} records"
    if result.duplicates:
        message += f" (skipped {result.duplicates} duplicates)"
    if result.missing:
        message += f" ({result.missing} missing records skipped)"
    if getattr(result, "inaccessible", 0):
        message += f" ({result.inaccessible} inaccessible records skipped)"
    return ActionResponse(
        status="success",
        message=message,
        data={"count": result.count, "duplicates": result.duplicates, "updated": result.updated, "missing": result.missing, "inaccessible": getattr(result, "inaccessible", 0)},
    )


@router.get("/{entity}/export")
async def export_entity(
    entity: str,
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    model = get_entity_model(entity)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    query = await row_scope_service.apply_scope_to_query(
        select(model),
        model,
        entity,
        str(user.id),
        user.role_ids,
        user.roles or [],
        user.is_superuser,
    )
    records = (await db.execute(query)).scalars().all()
    content = ie.export_records(meta, records, format=format)
    
    if format == "xlsx":
        filename = f"{entity}_export.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        filename = f"{entity}_export.csv"
        media_type = "text/csv"
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{entity}/exportable-fields")
async def get_exportable_fields(
    entity: str,
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    fields = ie.get_exportable_fields(meta)
    return ActionResponse(status="success", message="OK", data={"fields": fields})


@router.post("/{entity}/export-custom")
async def export_entity_custom(
    entity: str,
    payload: CustomExportRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user_from_token),
    rbac: RBACAppService = Depends(get_rbac_service),
    row_scope_service: RowScopeService = Depends(get_row_scope_service),
):
    meta = MetaRegistry.get(entity)
    if not meta:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    model = get_entity_model(entity)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if payload.format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail="Invalid format")

    fields = payload.fields or ie.get_export_fields(meta)

    stmt = select(model)
    if payload.record_ids:
        stmt = stmt.where(model.id.in_(payload.record_ids))
    stmt = await row_scope_service.apply_scope_to_query(
        stmt,
        model,
        entity,
        str(user.id),
        user.role_ids,
        user.roles or [],
        user.is_superuser,
    )
    records = (await db.execute(stmt)).scalars().all()

    record_dicts = [
        {f.name: getattr(record, f.name, None) for f in meta.fields}
        for record in records
    ]
    link_titles_list = await build_link_titles_batch(db, meta, record_dicts)

    content = ie.export_records_custom(
        meta, records, fields, link_titles_list, format=payload.format
    )

    if payload.format == "xlsx":
        filename = f"{entity}_export.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        filename = f"{entity}_export.csv"
        media_type = "text/csv"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
