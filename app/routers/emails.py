import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Email, EmailAccount, Folder

router = APIRouter(prefix="/api/emails", tags=["emails"])

SYSTEM_FOLDERS = {"INBOX", "SENT", "DRAFTS", "STARRED"}
VIRTUAL_FOLDERS = {"SNOOZED"}


async def _validate_folder(folder: str, db: AsyncSession) -> str:
    """Return the normalized folder name if it exists (system or user-defined), else 400."""
    normalized = folder.upper().strip()
    if normalized == "STARRED":
        return normalized
    if normalized in SYSTEM_FOLDERS:
        return normalized
    if normalized in VIRTUAL_FOLDERS:
        return normalized
    result = await db.execute(select(Folder).where(Folder.normalized_name == normalized))
    if result.scalar_one_or_none() is None:
        raise HTTPException(400, f"Unknown folder '{folder}'")
    return normalized


class EmailResponse(BaseModel):
    id: int
    account_id: int
    account_email: str = ""
    from_address: str
    from_name: str | None
    to_addresses: str
    subject: str
    body_text: str | None
    is_read: bool
    is_starred: bool
    folder: str
    snoozed_until: str | None = None
    send_at: str | None = None
    received_at: str


class SendEmailRequest(BaseModel):
    account_id: int
    to: str
    subject: str
    body: str = ""


class SaveDraftRequest(BaseModel):
    account_id: int
    to: str = ""
    subject: str = ""
    body: str = ""


class MoveEmailRequest(BaseModel):
    folder: str


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _email_to_response(e: Email, account_email: str = "") -> EmailResponse:
    return EmailResponse(
        id=e.id, account_id=e.account_id, account_email=account_email,
        from_address=e.from_address, from_name=e.from_name,
        to_addresses=e.to_addresses, subject=e.subject,
        body_text=e.body_text, is_read=e.is_read, is_starred=e.is_starred,
        folder=e.folder,
        snoozed_until=e.snoozed_until.isoformat() if e.snoozed_until else None,
        send_at=e.send_at.isoformat() if e.send_at else None,
        received_at=e.received_at.isoformat(),
    )


def _parse_iso_datetime(value: str, field: str) -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(400, f"Invalid datetime for '{field}'. Use ISO format (e.g. 2026-07-15T14:00:00)")
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.UTC).replace(tzinfo=None)
    return dt


@router.get("", response_model=list[EmailResponse])
async def list_emails(
    response: Response,
    folder: str = Query("INBOX"),
    account_id: int | None = Query(None, ge=1),
    q_search: str | None = Query(None, alias="q", max_length=256),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    folder = await _validate_folder(folder, db)
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

    q = select(Email)
    if folder == "SNOOZED":
        q = q.where(Email.snoozed_until.isnot(None), Email.snoozed_until > now)
    elif folder == "STARRED":
        q = q.where(Email.is_starred == True)
    else:
        q = q.where(Email.folder == folder)
        q = q.where(Email.snoozed_until.is_(None))
        q = q.where(Email.send_at.is_(None))
    if account_id is not None:
        q = q.where(Email.account_id == account_id)
    if q_search:
        pattern = f"%{q_search}%"
        q = q.where(
            Email.subject.ilike(pattern)
            | Email.from_address.ilike(pattern)
            | Email.from_name.ilike(pattern)
            | Email.body_text.ilike(pattern)
        )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(desc(Email.received_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    emails = result.scalars().all()

    accounts = {}
    if emails:
        acc_result = await db.execute(select(EmailAccount))
        for a in acc_result.scalars().all():
            accounts[a.id] = a.email

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)

    return [_email_to_response(e, accounts.get(e.account_id, "")) for e in emails]


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db)):
    """Total unread INBOX emails — powers the sidebar badge regardless of current page/folder."""
    count = (
        await db.execute(
            select(func.count()).select_from(Email).where(
                Email.folder == "INBOX", Email.is_read == False
            )
        )
    ).scalar() or 0
    return {"unread": count}


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")

    account_email = ""
    acc = await db.execute(select(EmailAccount).where(EmailAccount.id == email.account_id))
    account = acc.scalar_one_or_none()
    if account:
        account_email = account.email

    return _email_to_response(email, account_email)


@router.post("/{email_id}/mark-read")
async def mark_read(email_id: int, db: AsyncSession = Depends(get_db)):
    """Explicit mark-as-read — GET /{id} no longer mutates state."""
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    if not email.is_read:
        email.is_read = True
        await db.commit()
    return {"id": email.id, "is_read": True}


@router.post("/send", response_model=EmailResponse, status_code=201)
async def send_email(req: SendEmailRequest, db: AsyncSession = Depends(get_db)):
    if not req.to.strip():
        raise HTTPException(400, "Recipient ('to') is required")
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == req.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    now = _utcnow()
    email = Email(
        account_id=req.account_id,
        provider_message_id=f"sent-{now.timestamp()}",
        from_address=account.email,
        from_name=account.display_name,
        to_addresses=req.to,
        subject=req.subject,
        body_text=req.body,
        is_read=True,
        folder="SENT",
        received_at=now,
        send_at=now + datetime.timedelta(seconds=10),
    )
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return _email_to_response(email, account.email)


@router.post("/draft", response_model=EmailResponse, status_code=201)
async def save_draft(req: SaveDraftRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == req.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    now = _utcnow()
    email = Email(
        account_id=req.account_id,
        provider_message_id=f"draft-{now.timestamp()}",
        from_address=account.email,
        from_name=account.display_name,
        to_addresses=req.to,
        subject=req.subject,
        body_text=req.body,
        is_read=True,
        folder="DRAFTS",
        received_at=now,
    )
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return _email_to_response(email, account.email)


@router.post("/{email_id}/toggle-read")
async def toggle_read(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    email.is_read = not email.is_read
    await db.commit()
    return {"id": email.id, "is_read": email.is_read}


@router.post("/{email_id}/toggle-star")
async def toggle_star(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    email.is_starred = not email.is_starred
    await db.commit()
    return {"id": email.id, "is_starred": email.is_starred}


@router.post("/{email_id}/move")
async def move_email(email_id: int, req: MoveEmailRequest, db: AsyncSession = Depends(get_db)):
    folder = await _validate_folder(req.folder, db)
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    email.folder = folder
    if folder == "INBOX":
        email.is_read = False
    await db.commit()
    return {"id": email.id, "folder": folder}


@router.delete("/{email_id}")
async def delete_email(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    await db.delete(email)
    await db.commit()
    return {"deleted": email_id}


class SnoozeRequest(BaseModel):
    until: str


@router.post("/{email_id}/snooze")
async def snooze_email(email_id: int, req: SnoozeRequest, db: AsyncSession = Depends(get_db)):
    until = _parse_iso_datetime(req.until, "until")
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    email.snoozed_until = until
    await db.commit()
    return {"id": email.id, "snoozed_until": until.isoformat()}


@router.post("/{email_id}/unsnooze")
async def unsnooze_email(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    email.snoozed_until = None
    await db.commit()
    return {"id": email.id, "snoozed_until": None}


@router.post("/{email_id}/undo-send")
async def undo_send(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    if email.send_at is None:
        raise HTTPException(400, "Email has no pending send")
    await db.delete(email)
    await db.commit()
    return {"deleted": email_id}
