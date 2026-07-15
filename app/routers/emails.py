from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Email, EmailAccount

router = APIRouter(prefix="/api/emails", tags=["emails"])

FOLDERS = ["INBOX", "SENT", "DRAFTS", "STARRED"]


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


def _email_to_response(e: Email, account_email: str = "") -> EmailResponse:
    return EmailResponse(
        id=e.id, account_id=e.account_id, account_email=account_email,
        from_address=e.from_address, from_name=e.from_name,
        to_addresses=e.to_addresses, subject=e.subject,
        body_text=e.body_text, is_read=e.is_read, is_starred=e.is_starred,
        folder=e.folder, received_at=e.received_at.isoformat(),
    )


@router.get("", response_model=list[EmailResponse])
async def list_emails(
    folder: str = Query("INBOX"),
    account_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Email)
    if folder.upper() in FOLDERS:
        if folder.upper() == "STARRED":
            q = q.where(Email.is_starred == True)
        else:
            q = q.where(Email.folder == folder.upper())
    if account_id:
        q = q.where(Email.account_id == account_id)

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

    if response is not None:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)

    return [_email_to_response(e, accounts.get(e.account_id, "")) for e in emails]


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    if not email.is_read:
        email.is_read = True
        await db.commit()
    return _email_to_response(email)


@router.post("/send")
async def send_email(req: SendEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == req.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    import datetime
    email = Email(
        account_id=req.account_id,
        provider_message_id=f"sent-{datetime.datetime.now(datetime.UTC).timestamp()}",
        from_address=account.email,
        from_name=account.display_name,
        to_addresses=req.to,
        subject=req.subject,
        body_text=req.body,
        is_read=True,
        folder="SENT",
        received_at=datetime.datetime.now(datetime.UTC),
    )
    db.add(email)
    await db.commit()
    await db.refresh(email)
    return _email_to_response(email, account.email)


@router.post("/draft")
async def save_draft(req: SaveDraftRequest, db: AsyncSession = Depends(get_db)):
    import datetime
    result = await db.execute(select(EmailAccount).where(EmailAccount.id == req.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Account not found")

    email = Email(
        account_id=req.account_id,
        provider_message_id=f"draft-{datetime.datetime.now(datetime.UTC).timestamp()}",
        from_address=account.email,
        from_name=account.display_name,
        to_addresses=req.to,
        subject=req.subject,
        body_text=req.body,
        is_read=True,
        folder="DRAFTS",
        received_at=datetime.datetime.now(datetime.UTC),
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


@router.delete("/{email_id}")
async def delete_email(email_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(404, "Email not found")
    await db.delete(email)
    await db.commit()
    return {"deleted": email_id}
