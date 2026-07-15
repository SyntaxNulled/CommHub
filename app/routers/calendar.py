import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import CalendarEvent, EmailAccount

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class EventCreate(BaseModel):
    account_id: int = 1
    title: str
    description: str = ""
    location: str = ""
    start_time: str
    end_time: str
    is_all_day: bool = False


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_all_day: bool | None = None


class EventResponse(BaseModel):
    id: int
    account_id: int
    title: str
    description: str | None
    location: str | None
    start_time: str
    end_time: str
    is_all_day: bool


def _event_to_response(e: CalendarEvent) -> EventResponse:
    return EventResponse(
        id=e.id, account_id=e.account_id, title=e.title,
        description=e.description, location=e.location,
        start_time=e.start_time.isoformat(), end_time=e.end_time.isoformat(),
        is_all_day=e.is_all_day,
    )


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    start: str | None = Query(None),
    end: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(CalendarEvent).order_by(CalendarEvent.start_time)

    if start:
        try:
            start_dt = datetime.datetime.fromisoformat(start)
            q = q.where(CalendarEvent.start_time >= start_dt)
        except ValueError:
            pass
    if end:
        try:
            end_dt = datetime.datetime.fromisoformat(end)
            q = q.where(CalendarEvent.end_time <= end_dt)
        except ValueError:
            pass

    result = await db.execute(q)
    return [_event_to_response(e) for e in result.scalars().all()]


@router.post("/events", response_model=EventResponse)
async def create_event(evt: EventCreate, db: AsyncSession = Depends(get_db)):
    try:
        start = datetime.datetime.fromisoformat(evt.start_time)
        end = datetime.datetime.fromisoformat(evt.end_time)
    except ValueError:
        raise HTTPException(400, "Invalid datetime format. Use ISO format (e.g. 2026-07-15T14:00:00)")

    record = CalendarEvent(
        account_id=evt.account_id,
        provider_event_id=f"local-{datetime.datetime.utcnow().timestamp()}",
        title=evt.title, description=evt.description, location=evt.location,
        start_time=start, end_time=end, is_all_day=evt.is_all_day,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _event_to_response(record)


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: int, evt: EventUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Event not found")

    updates = evt.model_dump(exclude_unset=True)
    if "start_time" in updates:
        updates["start_time"] = datetime.datetime.fromisoformat(updates["start_time"])
    if "end_time" in updates:
        updates["end_time"] = datetime.datetime.fromisoformat(updates["end_time"])

    for field, value in updates.items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return _event_to_response(record)


@router.delete("/events/{event_id}")
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Event not found")
    await db.delete(record)
    await db.commit()
    return {"deleted": event_id}
