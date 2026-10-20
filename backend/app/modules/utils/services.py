"""
Utils domain services: link shortener, QR generator, and shared security helpers.
"""
from __future__ import annotations

import base64
import hashlib
import html
import io
import re
import secrets
import string
from collections import Counter
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import bcrypt
import qrcode
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse, Response
from PIL import ImageColor
from qrcode.image.svg import SvgPathImage
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.naming_service import NamingAppService
from app.core.config import settings
from app.core.database import async_session_maker
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.security import get_password_hash
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.meta.registry import MetaRegistry
from app.modules.collaboration_audit.services import AuditLogService, NotificationService
from app.modules.utils.models import QrCode, ShortLink, ShortLinkClick
from app.modules.utils.rate_limiter import utils_rate_limiter


SLUG_ALPHABET = string.ascii_letters + string.digits
SLUG_CHARSET = SLUG_ALPHABET + "_-"
MAX_URL_LENGTH = 2048
MAX_QR_LENGTH = 4096
SENSITIVE_PARAMS = {"token", "password", "api_key", "apikey", "secret", "auth"}
LINK_CREATE_LIMIT = 20
LINK_CREATE_WINDOW = 60
QR_CREATE_LIMIT = 30
QR_CREATE_WINDOW = 60
REDIRECT_LIMIT = 100
REDIRECT_WINDOW = 60
GLOBAL_PREVIEW_ENABLED = False

BLOCKED_HOSTS = {
    "malware.example.com",
    "phishing.example.com",
    "evil.test",
    "malicious.local",
}

ERROR_CORRECTION_MAP = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}

HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}){1,2}$")


def _now() -> datetime:
    return datetime.utcnow()


def _validate_scheme(url: str) -> None:
    if not url:
        raise BadRequestError("URL is required")
    lowered = url.strip().lower()
    for bad in ("javascript:", "data:", "vbscript:"):
        if lowered.startswith(bad):
            raise BadRequestError(f"Disallowed URI scheme: {bad.rstrip(':')}")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise BadRequestError("Only http and https URLs are allowed")
    if not parsed.netloc:
        raise BadRequestError("Invalid URL: missing host")


def validate_url(url: str) -> str:
    url = str(url or "").strip()
    if len(url) > MAX_URL_LENGTH:
        raise BadRequestError(f"URL exceeds maximum length of {MAX_URL_LENGTH}")
    _validate_scheme(url)
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if any(h in host.lower() for h in BLOCKED_HOSTS):
        raise BadRequestError("Destination has been blocked")
    return parsed.geturl()


def validate_qr_input(value: str, source_type: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise BadRequestError("QR input is required")
    lowered = value.lower()
    for bad in ("javascript:", "data:", "vbscript:"):
        if lowered.startswith(bad):
            raise BadRequestError(f"Disallowed URI scheme: {bad.rstrip(':')}")
    if source_type in ("url", "short_link"):
        return validate_url(value)
    if len(value) > MAX_QR_LENGTH:
        raise BadRequestError(f"QR text exceeds maximum length of {MAX_QR_LENGTH}")
    return value


def _short_url(slug: str) -> str:
    return f"{settings.PUBLIC_APP_URL.rstrip('/')}/{slug}"


def _hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _redact_referer(referer: str | None) -> str | None:
    if not referer:
        return None
    try:
        p = urlparse(referer)
        clean = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
        return clean[:512]
    except Exception:
        return referer[:512]


def _hash_password(password: str) -> str:
    return get_password_hash(password)


def _check_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _is_owner_or_admin(record: Any, user: Any) -> bool:
    return user.is_superuser or getattr(record, "created_by") == user.id


def _coerce_short_link_data(data: dict[str, Any]) -> dict[str, Any]:
    from app.application.services.entity_service import EntityService
    return EntityService.coerce_incoming_types(ShortLink, data)


async def _unique_slug(db: AsyncSession, custom: str | None = None) -> str:
    if custom:
        slug = custom.strip()
        if not (3 <= len(slug) <= 32 and re.match(r"^[A-Za-z0-9_-]+$", slug)):
            raise BadRequestError("Custom slug must be 3-32 alphanumeric, dash, or underscore")
        existing = (await db.execute(select(ShortLink.id).where(ShortLink.slug == slug))).scalar_one_or_none()
        if existing:
            raise BadRequestError("Custom slug is already in use")
        return slug

    for _ in range(10):
        slug = "".join(secrets.choice(SLUG_ALPHABET) for _ in range(7))
        existing = (await db.execute(select(ShortLink.id).where(ShortLink.slug == slug))).scalar_one_or_none()
        if not existing:
            return slug
    raise BadRequestError("Unable to generate a unique slug")


async def _generate_id(db: AsyncSession, entity: str) -> str:
    meta = MetaRegistry.get(entity)
    naming_service = NamingAppService(NamingRepository(db))
    return await naming_service.generate_id(meta.naming, entity) if meta and meta.naming else None


async def _check_rate(key: str, limit: int, window: int) -> None:
    allowed, retry_after = await utils_rate_limiter.is_allowed(key, limit, window)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


class UtilsService:
    """Application services for the Utils module."""

    # ------------------------------------------------------------------
    # Short links
    # ------------------------------------------------------------------
    @staticmethod
    async def create_short_link(db: AsyncSession, user: Any, data: dict[str, Any]) -> ShortLink:
        await _check_rate(f"link_create:{user.id}", LINK_CREATE_LIMIT, LINK_CREATE_WINDOW)

        destination_url = str(data.get("destination_url") or "").strip()
        validate_url(destination_url)

        custom_slug = str(data.get("custom_slug") or data.get("slug") or "").strip()
        slug = await _unique_slug(db, custom_slug)

        payload = _coerce_short_link_data(data)
        payload["slug"] = slug
        payload["destination_url"] = destination_url
        payload["is_active"] = True
        payload["click_count"] = 0
        payload["created_by"] = user.id
        payload["last_modified_by"] = user.id

        if payload.get("password"):
            payload["password_hash"] = _hash_password(payload.pop("password"))
        else:
            payload.pop("password", None)
            payload["password_hash"] = None

        payload["show_preview"] = bool(payload.get("show_preview", False))

        generated_id = await _generate_id(db, "short_link")
        payload["id"] = generated_id

        record = ShortLink(**payload)
        db.add(record)
        await db.flush()
        await db.refresh(record)

        await AuditLogService.log_event(
            db,
            entity="short_link",
            record_id=record.id,
            action="create",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(record),
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def list_short_links(
        db: AsyncSession,
        user: Any,
        status_filter: str = "all",
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        query = select(ShortLink).order_by(ShortLink.created_at.desc())
        if not user.is_superuser:
            query = query.where(ShortLink.created_by == user.id)

        now = _now()
        if status_filter == "active":
            query = query.where(
                ShortLink.is_active == True,
                or_(ShortLink.expires_at.is_(None), ShortLink.expires_at > now),
            )
        elif status_filter == "inactive":
            query = query.where(ShortLink.is_active == False)
        elif status_filter == "expired":
            query = query.where(
                or_(
                    ShortLink.is_active == False,
                    and_(ShortLink.expires_at.isnot(None), ShortLink.expires_at < now),
                )
            )

        if search:
            like = f"%{search}%"
            query = query.where(or_(ShortLink.slug.ilike(like), ShortLink.title.ilike(like)))

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        records = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return {
            "data": [record_to_dict(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_short_link(db: AsyncSession, user: Any, record_id: str) -> dict[str, Any]:
        record = await db.get(ShortLink, record_id)
        if not record:
            raise NotFoundError("Short Link", record_id)
        if not _is_owner_or_admin(record, user):
            raise ForbiddenError("You do not own this link")

        clicks = (
            await db.execute(
                select(ShortLinkClick)
                .where(ShortLinkClick.short_link_id == record.id)
                .order_by(ShortLinkClick.clicked_at.desc())
                .limit(10)
            )
        ).scalars().all()

        total_clicks = (
            await db.execute(select(func.count()).where(ShortLinkClick.short_link_id == record.id))
        ).scalar() or 0

        referer_counts = Counter(c.referer or "direct" for c in clicks)
        country_counts = Counter(c.country or "unknown" for c in clicks)

        return {
            "record": record_to_dict(record),
            "analytics": {
                "total_clicks": total_clicks,
                "recent_clicks": [record_to_dict(c) for c in clicks],
                "referers": [{"name": k, "count": v} for k, v in referer_counts.items()],
                "countries": [{"name": k, "count": v} for k, v in country_counts.items()],
            },
        }

    @staticmethod
    async def update_short_link(db: AsyncSession, user: Any, record_id: str, data: dict[str, Any]) -> ShortLink:
        record = await db.get(ShortLink, record_id)
        if not record:
            raise NotFoundError("Short Link", record_id)
        if not _is_owner_or_admin(record, user):
            raise ForbiddenError("You do not own this link")

        old = record_to_dict(record)
        payload = _coerce_short_link_data(data)

        allowed = {"destination_url", "title", "expires_at", "is_active", "show_preview"}
        for key, value in payload.items():
            if key not in allowed:
                continue
            if key == "destination_url" and value:
                validate_url(value)
                record.destination_url = value
            elif key == "is_active":
                record.is_active = bool(value)
            elif key == "show_preview":
                record.show_preview = bool(value)
            elif hasattr(record, key):
                setattr(record, key, value)

        if "password" in data:
            password = data.get("password")
            record.password_hash = _hash_password(password) if password else None

        record.last_modified_by = user.id
        await db.flush()
        await db.refresh(record)

        await AuditLogService.log_event(
            db,
            entity="short_link",
            record_id=record.id,
            action="update",
            actor_id=user.id,
            old_values=old,
            new_values=record_to_dict(record),
        )
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def redirect(db: AsyncSession, slug: str, request: Any) -> Response:
        client_ip = request.client.host if request.client else None
        await _check_rate(f"redirect:{_hash_ip(client_ip) or 'anon'}", REDIRECT_LIMIT, REDIRECT_WINDOW)

        record = (await db.execute(select(ShortLink).where(ShortLink.slug == slug))).scalar_one_or_none()
        if not record:
            return Response("Gone", status_code=status.HTTP_410_GONE)

        now = _now()
        if not record.is_active or (record.expires_at and record.expires_at < now):
            return Response("Gone", status_code=status.HTTP_410_GONE)

        password_param = request.query_params.get("password")
        if record.password_hash:
            if not password_param or not _check_password(password_param, record.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Password required",
                    headers={"WWW-Authenticate": "form"},
                )

        confirm = request.query_params.get("confirm") in ("1", "true", "yes")
        if (record.show_preview or GLOBAL_PREVIEW_ENABLED) and not confirm:
            return _preview_response(record)

        click_id = await _generate_id(db, "short_link_click")
        click = ShortLinkClick(
            id=click_id,
            short_link_id=record.id,
            clicked_at=now,
            ip_hash=_hash_ip(client_ip),
            user_agent=(request.headers.get("user-agent") or "")[:512],
            referer=_redact_referer(request.headers.get("referer")),
            country=None,
        )
        db.add(click)
        record.click_count = (record.click_count or 0) + 1
        await db.commit()

        return RedirectResponse(
            record.destination_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Referrer-Policy": "no-referrer"},
        )

    # ------------------------------------------------------------------
    # QR codes
    # ------------------------------------------------------------------
    @staticmethod
    async def create_qr_code(db: AsyncSession, user: Any, data: dict[str, Any]) -> dict[str, Any]:
        await _check_rate(f"qr_create:{user.id}", QR_CREATE_LIMIT, QR_CREATE_WINDOW)

        source_type = str(data.get("source_type") or "url")
        if source_type not in ("url", "text", "short_link"):
            raise BadRequestError("Invalid source_type")

        source_value = str(data.get("source_value") or "").strip()
        short_link_id = data.get("short_link_id")

        if source_type == "short_link":
            if not short_link_id:
                raise BadRequestError("short_link_id is required for short_link source")
            link = await db.get(ShortLink, short_link_id)
            if not link:
                raise NotFoundError("Short Link", short_link_id)
            source_value = _short_url(link.slug)
            short_link_id = link.id
        else:
            source_value = validate_qr_input(source_value, source_type)
            short_link_id = None

        ec = str(data.get("error_correction_level") or "M").upper()
        if ec not in ERROR_CORRECTION_MAP:
            raise BadRequestError("Invalid error correction level")

        try:
            size = int(data.get("size") or 256)
        except (ValueError, TypeError):
            raise BadRequestError("Size must be a valid integer")
        if not 50 <= size <= 1000:
            raise BadRequestError("Size must be between 50 and 1000")

        fmt = str(data.get("format") or "svg").lower()
        if fmt not in ("svg", "png"):
            raise BadRequestError("Format must be svg or png")

        fg_color = str(data.get("fg_color") or "#000000")
        bg_color = str(data.get("bg_color") or "#ffffff")
        if not HEX_COLOR_RE.match(fg_color) or not HEX_COLOR_RE.match(bg_color):
            raise BadRequestError("Colors must be valid hex codes")

        qr_id = await _generate_id(db, "qr_code")
        record = QrCode(
            id=qr_id,
            source_type=source_type,
            source_value=source_value,
            short_link_id=short_link_id,
            error_correction_level=ec,
            size=size,
            format=fmt,
            fg_color=fg_color,
            bg_color=bg_color,
            created_by=user.id,
            last_modified_by=user.id,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)

        await AuditLogService.log_event(
            db,
            entity="qr_code",
            record_id=record.id,
            action="create",
            actor_id=user.id,
            old_values=None,
            new_values=record_to_dict(record),
        )
        await db.commit()
        await db.refresh(record)

        data_url = await UtilsService._render_qr_data_url(record)
        return {
            "record": record_to_dict(record),
            "data_url": data_url,
            "download_url": f"/api/utils/qr/{record.id}/download?format={record.format}",
        }

    @staticmethod
    async def list_qr_codes(
        db: AsyncSession,
        user: Any,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        query = select(QrCode).order_by(QrCode.created_at.desc())
        if not user.is_superuser:
            query = query.where(QrCode.created_by == user.id)
        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
        records = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return {
            "data": [record_to_dict(r) for r in records],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_qr_code(db: AsyncSession, user: Any, record_id: str) -> dict[str, Any]:
        record = await db.get(QrCode, record_id)
        if not record:
            raise NotFoundError("QR Code", record_id)
        if not _is_owner_or_admin(record, user):
            raise ForbiddenError("You do not own this QR code")
        data_url = await UtilsService._render_qr_data_url(record)
        return {
            "record": record_to_dict(record),
            "data_url": data_url,
            "download_url": f"/api/utils/qr/{record.id}/download?format={record.format}",
        }

    @staticmethod
    async def download_qr(db: AsyncSession, user: Any, record_id: str, fmt: str | None = None) -> Response:
        record = await db.get(QrCode, record_id)
        if not record:
            raise NotFoundError("QR Code", record_id)
        if not _is_owner_or_admin(record, user):
            raise ForbiddenError("You do not own this QR code")

        fmt = (fmt or record.format).lower()
        if fmt not in ("svg", "png"):
            raise BadRequestError("Invalid format")

        if fmt == "svg":
            body = await UtilsService._render_svg(record)
            return Response(
                body,
                media_type="image/svg+xml",
                headers={
                    "Content-Disposition": f'attachment; filename="qr-{record.id}.svg"',
                    "Content-Security-Policy": "default-src 'none'",
                },
            )

        body = await UtilsService._render_png(record)
        return Response(
            body,
            media_type="image/png",
            headers={
                "Content-Disposition": f'attachment; filename="qr-{record.id}.png"',
            },
        )

    @staticmethod
    async def _render_qr_data_url(record: QrCode) -> str:
        if record.format == "svg":
            svg = await UtilsService._render_svg(record)
            b64 = base64.b64encode(svg.encode()).decode()
            return f"data:image/svg+xml;base64,{b64}"
        png = await UtilsService._render_png(record)
        b64 = base64.b64encode(png).decode()
        return f"data:image/png;base64,{b64}"

    @staticmethod
    async def _render_svg(record: QrCode) -> str:
        img = _qr_image(record)
        svg = img.to_string(encoding="unicode")
        fg = record.fg_color or "#000000"
        bg = record.bg_color or "#ffffff"
        # Remove qrcode-specific non-SVG attributes from the root <svg> tag
        svg = re.sub(r'\s+(fill_color|back_color)="[^"]*"', "", svg)
        # Insert a background rect immediately after the opening <svg> tag
        match = re.match(r"(<svg[^>]*>)", svg)
        if match:
            opening = match.group(1)
            rest = svg[match.end():]
            svg = opening + f'<rect width="100%" height="100%" fill="{bg}"/>' + rest
        # Ensure the path uses the requested foreground color
        svg = re.sub(
            r'(<path\b[^>]*)\bfill="[^"]*"',
            rf'\1fill="{fg}"',
            svg,
            count=1,
        )
        return svg

    @staticmethod
    async def _render_png(record: QrCode) -> bytes:
        qr_obj = qrcode.QRCode(
            error_correction=ERROR_CORRECTION_MAP[record.error_correction_level],
            box_size=max(2, record.size // 33),
            border=4,
        )
        qr_obj.add_data(record.source_value)
        qr_obj.make(fit=True)
        fg = ImageColor.getcolor(record.fg_color or "#000000", "RGB")
        bg = ImageColor.getcolor(record.bg_color or "#ffffff", "RGB")
        img = qr_obj.make_image(fill_color=fg, back_color=bg).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    async def scan_all_short_links() -> int:
        """Daily background scan: deactivate active links that are now on the blocklist."""
        blocked = 0
        async with async_session_maker() as db:
            now = _now()
            result = await db.execute(select(ShortLink).where(ShortLink.is_active == True))
            links = result.scalars().all()
            for link in links:
                if link.expires_at and link.expires_at < now:
                    link.is_active = False
                    continue
                try:
                    validate_url(link.destination_url)
                except BadRequestError:
                    old = {"is_active": True}
                    link.is_active = False
                    await AuditLogService.log_event(
                        db,
                        entity="short_link",
                        record_id=link.id,
                        action="update",
                        actor_id="system",
                        old_values=old,
                        new_values={"is_active": False, "reason": "blocklist_scan"},
                    )
                    await NotificationService.create_notification(
                        db,
                        user_id=link.created_by or "system",
                        reference_entity="short_link",
                        reference_id=link.id,
                        type="link_blocked",
                        message=f"Your short link {link.slug} was deactivated because its destination was flagged by a security scan.",
                        actor_id="system",
                    )
                    blocked += 1
            await db.commit()
        return blocked


def _qr_image(record: QrCode) -> SvgPathImage:
    qr_obj = qrcode.QRCode(
        error_correction=ERROR_CORRECTION_MAP[record.error_correction_level],
        box_size=max(2, record.size // 33),
        border=4,
    )
    qr_obj.add_data(record.source_value)
    qr_obj.make(fit=True)
    return qr_obj.make_image(
        image_factory=SvgPathImage,
        fill_color=record.fg_color or "#000000",
        back_color=record.bg_color or "#ffffff",
    )


def _preview_response(record: ShortLink) -> Response:
    dest = html.escape(record.destination_url or "")
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link Preview</title>
</head>
<body>
<h1>Warning: You are leaving this site</h1>
<p>This short link points to:</p>
<p><code>{dest}</code></p>
<p><a href="?confirm=1">Continue to destination</a></p>
</body>
</html>"""
    return Response(
        body,
        media_type="text/html",
        headers={
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'none'; object-src 'none'",
        },
    )
