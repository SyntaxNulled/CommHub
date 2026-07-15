from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Folder

router = APIRouter(prefix="/api/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    color: str | None = "blue"
    icon: str | None = "folder"


class FolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    color: str | None = None
    icon: str | None = None
    sort_order: int | None = None


class FolderResponse(BaseModel):
    id: int
    name: str
    normalized_name: str
    color: str | None
    icon: str | None
    is_system: bool
    sort_order: int


def _folder_response(f: Folder) -> FolderResponse:
    return FolderResponse(
        id=f.id, name=f.name, normalized_name=f.normalized_name,
        color=f.color, icon=f.icon, is_system=f.is_system, sort_order=f.sort_order,
    )


@router.get("", response_model=list[FolderResponse])
async def list_folders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Folder).order_by(Folder.is_system.desc(), Folder.sort_order, Folder.name)
    )
    return [_folder_response(f) for f in result.scalars().all()]


@router.post("", response_model=FolderResponse, status_code=201)
async def create_folder(folder: FolderCreate, db: AsyncSession = Depends(get_db)):
    normalized = folder.name.strip().upper()
    existing = await db.execute(select(Folder).where(Folder.normalized_name == normalized))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Folder '{folder.name}' already exists")

    record = Folder(
        name=folder.name.strip(),
        normalized_name=normalized,
        color=folder.color,
        icon=folder.icon,
        is_system=False,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _folder_response(record)


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(folder_id: int, folder: FolderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Folder not found")
    if record.is_system and folder.name is not None:
        raise HTTPException(400, "Cannot rename system folders")

    updates = folder.model_dump(exclude_unset=True)
    if "name" in updates:
        new_name = updates["name"].strip()
        new_normalized = new_name.upper()
        conflict = await db.execute(
            select(Folder).where(Folder.normalized_name == new_normalized, Folder.id != folder_id)
        )
        if conflict.scalar_one_or_none():
            raise HTTPException(409, f"Folder '{new_name}' already exists")
        updates["name"] = new_name
        updates["normalized_name"] = new_normalized

    for field, value in updates.items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return _folder_response(record)


@router.delete("/{folder_id}")
async def delete_folder(folder_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Folder not found")
    if record.is_system:
        raise HTTPException(400, "Cannot delete system folders")

    # Move emails in this folder back to INBOX before deleting the folder metadata
    from app.models import Email
    await db.execute(
        update(Email)
        .where(Email.folder == record.normalized_name)
        .values(folder="INBOX", is_read=False)
    )
    await db.delete(record)
    await db.commit()
    return {"deleted": folder_id}


@router.get("/valid/{folder_name}")
async def is_valid_folder(folder_name: str, db: AsyncSession = Depends(get_db)):
    """Return True if folder_name is a known system or user folder."""
    normalized = folder_name.strip().upper()
    result = await db.execute(select(Folder).where(Folder.normalized_name == normalized))
    return {"valid": result.scalar_one_or_none() is not None}
