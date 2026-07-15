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
    category: str | None = "other"
    rrule: str | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_all_day: bool | None = None
    category: str | None = None
    rrule: str | None = None


class EventResponse(BaseModel):
    id: int
    account_id: int
    title: str
    description: str | None
    location: str | None
    start_time: str
    end_time: str
    is_all_day: bool
    category: str | None
    rrule: str | None = None


# Default category colors used by the UI
CATEGORY_COLORS = {
    "work": "#2563EB",        # blue-600
    "personal": "#10B981",    # emerald-500
    "meeting": "#8B5CF6",     # violet-500
    "important": "#DC2626",   # red-600
    "travel": "#F59E0B",      # amber-500
    "birthday": "#EC4899",    # pink-500
    "reminder": "#6B7280",    # gray-500
    "other": "#3B82F6",       # blue-500
}

DEFAULT_CATEGORIES = list(CATEGORY_COLORS.keys())


def _event_to_response(e: CalendarEvent) -> EventResponse:
    return EventResponse(
        id=e.id, account_id=e.account_id, title=e.title,
        description=e.description, location=e.location,
        start_time=e.start_time.isoformat(), end_time=e.end_time.isoformat(),
        is_all_day=e.is_all_day, category=e.category, rrule=e.rrule,
    )


def _validate_rrule(rrule: str | None) -> None:
    if rrule is None:
        return
    from app.rrule import parse_rrule
    config = parse_rrule(rrule)
    if not config.get("freq"):
        raise HTTPException(400, f"Invalid rrule '{rrule}': FREQ is required")
    if config["freq"] not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        raise HTTPException(400, f"Invalid rrule freq '{config['freq']}'. Must be DAILY, WEEKLY, MONTHLY, or YEARLY")


def _parse_iso(value: str, field: str) -> datetime.datetime:
    """Parse ISO datetime and normalize to naive UTC so DB comparisons never mix aware/naive."""
    try:
        dt = datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(400, f"Invalid datetime for '{field}'. Use ISO format (e.g. 2026-07-15T14:00:00)")
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.UTC).replace(tzinfo=None)
    return dt


@router.get("/categories")
async def list_categories():
    """Return the default event categories and their color codes."""
    return [{"name": k, "color": v} for k, v in CATEGORY_COLORS.items()]


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    start: str | None = Query(None),
    end: str | None = Query(None),
    account_id: int | None = Query(None, ge=1),
    category: str | None = Query(None, max_length=64),
    db: AsyncSession = Depends(get_db),
):
    from app.rrule import expand_recurring

    range_start = _parse_iso(start, "start") if start else datetime.datetime.min
    range_end = _parse_iso(end, "end") if end else datetime.datetime.max

    q = select(CalendarEvent).order_by(CalendarEvent.start_time)
    if start:
        q = q.where(CalendarEvent.start_time <= range_end)
    if end:
        q = q.where(CalendarEvent.end_time >= range_start)
    if account_id is not None:
        q = q.where(CalendarEvent.account_id == account_id)
    if category:
        q = q.where(CalendarEvent.category == category)

    result = await db.execute(q)
    raw_events = result.scalars().all()

    expanded = []
    for e in raw_events:
        instances = expand_recurring(e.start_time, e.end_time, e.rrule, range_start, range_end)
        for inst in instances:
            virtual_id = e.id if len(instances) == 1 else None
            expanded.append({**e.__dict__, "start_time": inst["start_time"], "end_time": inst["end_time"], "virtual_id": virtual_id})

    return [
        EventResponse(
            id=evt.get("virtual_id") or evt["id"], account_id=evt["account_id"],
            title=evt["title"], description=evt.get("description"),
            location=evt.get("location"),
            start_time=evt["start_time"].isoformat(), end_time=evt["end_time"].isoformat(),
            is_all_day=evt["is_all_day"], category=evt.get("category"), rrule=evt.get("rrule"),
        )
        for evt in expanded
    ]


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(evt: EventCreate, db: AsyncSession = Depends(get_db)):
    start = _parse_iso(evt.start_time, "start_time")
    end = _parse_iso(evt.end_time, "end_time")
    if end < start:
        raise HTTPException(400, "end_time must be after start_time")
    _validate_rrule(evt.rrule)

    record = CalendarEvent(
        account_id=evt.account_id,
        provider_event_id=f"local-{datetime.datetime.now(datetime.UTC).timestamp()}",
        title=evt.title, description=evt.description, location=evt.location,
        start_time=start, end_time=end, is_all_day=evt.is_all_day,
        category=evt.category, rrule=evt.rrule,
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
        updates["start_time"] = _parse_iso(updates["start_time"], "start_time")
    if "end_time" in updates:
        updates["end_time"] = _parse_iso(updates["end_time"], "end_time")

    new_start = updates.get("start_time", record.start_time)
    new_end = updates.get("end_time", record.end_time)
    if new_end < new_start:
        raise HTTPException(400, "end_time must be after start_time")

    if "rrule" in updates:
        _validate_rrule(updates["rrule"])

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
