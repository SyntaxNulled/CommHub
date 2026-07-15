from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import EmailAccount

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountResponse(BaseModel):
    id: int
    email: str
    provider: str
    display_name: str | None
    is_active: bool


@router.get("", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).order_by(EmailAccount.id))
    return [
        AccountResponse(
            id=a.id, email=a.email, provider=a.provider.value,
            display_name=a.display_name, is_active=a.is_active,
        )
        for a in result.scalars().all()
    ]
