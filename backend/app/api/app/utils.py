"""
Utils app endpoints — link shortener and QR generator.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.security import CurrentUser, require_authenticated_user
from app.core.serialization import record_to_dict
from app.modules.utils.services import UtilsService
from app.schemas.base import ActionResponse

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post("/links")
async def create_short_link(
    payload: dict[str, Any],
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    record = await UtilsService.create_short_link(db, current_user, payload)
    return ActionResponse(
        status="success",
        message="Short link created",
        data=record_to_dict(record),
    )


@router.get("/links")
async def list_short_links(
    status: str = Query("all", pattern="^(all|active|inactive|expired)$"),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    result = await UtilsService.list_short_links(
        db, current_user, status_filter=status, search=search, page=page, page_size=page_size
    )
    return ActionResponse(status="success", message="Links loaded", data=result)


@router.get("/links/{link_id}")
async def get_short_link(
    link_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    result = await UtilsService.get_short_link(db, current_user, link_id)
    return ActionResponse(status="success", message="Link loaded", data=result)


@router.patch("/links/{link_id}")
async def update_short_link(
    link_id: str,
    payload: dict[str, Any],
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    record = await UtilsService.update_short_link(db, current_user, link_id, payload)
    return ActionResponse(
        status="success",
        message="Short link updated",
        data=record_to_dict(record),
    )


@router.get("/go/{slug}")
async def redirect_short_link(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    return await UtilsService.redirect(db, slug, request)


@router.post("/qr/generate")
async def generate_qr(
    payload: dict[str, Any],
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    result = await UtilsService.create_qr_code(db, current_user, payload)
    return ActionResponse(status="success", message="QR code generated", data=result)


@router.get("/qr")
async def list_qr_codes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    result = await UtilsService.list_qr_codes(db, current_user, page=page, page_size=page_size)
    return ActionResponse(status="success", message="QR codes loaded", data=result)


@router.get("/qr/{qr_id}")
async def get_qr_code(
    qr_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    result = await UtilsService.get_qr_code(db, current_user, qr_id)
    return ActionResponse(status="success", message="QR code loaded", data=result)


@router.get("/qr/{qr_id}/download")
async def download_qr(
    qr_id: str,
    format: str | None = Query(None, pattern="^(svg|png)$"),
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    return await UtilsService.download_qr(db, current_user, qr_id, fmt=format)
