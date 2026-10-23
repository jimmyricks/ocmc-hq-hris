from datetime import datetime
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.core.config import settings
from app.core.security import CurrentUser, require_system_admin_user
from app.modules.project_tasks.bahandi_integration import (
    authenticate_feed,
    build_artist_feed,
    issue_feed_credential,
    process_press_outbox,
    revoke_feed_credential,
)
from app.modules.project_tasks.models import BahandiPressOutbox

router = APIRouter(prefix="/integrations/bahandi/v1", tags=["Bahandi Integration"])


@router.get("/artists/{artist_id}/feed")
async def get_artist_feed(
    artist_id: int,
    response: Response,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not await authenticate_feed(db, artist_id, token):
        raise HTTPException(status_code=401, detail="Invalid integration credentials")
    response.headers["Cache-Control"] = "private, no-store"
    return await build_artist_feed(db, artist_id)


@router.post("/credentials/{artist_id}")
async def create_feed_credential(
    artist_id: int,
    response: Response,
    actor: CurrentUser = Depends(require_system_admin_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    token = await issue_feed_credential(db, artist_id, actor)
    return {"artistId": artist_id, "token": token}


@router.delete("/credentials/{artist_id}", status_code=204)
async def delete_feed_credential(
    artist_id: int,
    actor: CurrentUser = Depends(require_system_admin_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_feed_credential(db, artist_id, actor)
    return Response(status_code=204)


@router.post("/press-outbox/process")
async def run_press_outbox(
    db: AsyncSession = Depends(get_db),
    worker_token: str | None = Header(default=None, alias="X-Bahandi-Worker-Token"),
):
    _require_worker_token(worker_token)
    return await process_press_outbox(db)


def _require_worker_token(worker_token: str | None) -> None:
    expected = settings.BAHANDI_INTEGRATION_WORKER_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="Integration worker is not configured")
    if not worker_token or not hmac.compare_digest(worker_token, expected):
        raise HTTPException(status_code=401, detail="Invalid worker credentials")


@router.get("/press-outbox")
async def list_press_outbox(
    actor: CurrentUser = Depends(require_system_admin_user),
    db: AsyncSession = Depends(get_db),
):
    rows = list(
        (
            await db.scalars(
                select(BahandiPressOutbox)
                .order_by(BahandiPressOutbox.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    return [
        {
            "id": row.id,
            "sourceTaskId": row.source_task_id,
            "sourceSubmissionId": row.source_submission_id,
            "status": row.status,
            "attempts": row.attempts,
            "runAt": row.run_at.isoformat(),
            "completedAt": row.completed_at.isoformat() if row.completed_at else None,
            "lastError": row.last_error,
        }
        for row in rows
    ]


@router.post("/press-outbox/{outbox_id}/retry")
async def retry_press_outbox(
    outbox_id: int,
    worker_token: str | None = Header(default=None, alias="X-Bahandi-Worker-Token"),
    db: AsyncSession = Depends(get_db),
):
    _require_worker_token(worker_token)
    row = await db.get(BahandiPressOutbox, outbox_id)
    if not row:
        raise HTTPException(status_code=404, detail="Outbox record not found")
    if row.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed deliveries can be retried")
    row.status = "queued"
    row.attempts = 0
    row.run_at = datetime.utcnow()
    row.locked_at = None
    row.completed_at = None
    row.last_error = ""
    await db.commit()
    return {"id": row.id, "status": row.status}
