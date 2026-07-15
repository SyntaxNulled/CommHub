import datetime
import urllib.parse
import pytest
from app.models import EmailAccount, CalendarEvent, ProviderType


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class TestCalendarRRule:
    @pytest.mark.asyncio
    async def test_create_recurring_event(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        now = _utcnow()
        resp = await client.post("/api/calendar/events", json={
            "account_id": acct.id, "title": "Standup",
            "start_time": now.isoformat(), "end_time": (now + datetime.timedelta(hours=1)).isoformat(),
            "rrule": "FREQ=WEEKLY;COUNT=10",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["rrule"] == "FREQ=WEEKLY;COUNT=10"

    @pytest.mark.asyncio
    async def test_list_recurring_expands(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        now = _utcnow()
        event = CalendarEvent(
            account_id=acct.id, provider_event_id="mock-recur-1",
            title="Daily Standup", category="meeting",
            start_time=now - datetime.timedelta(days=1),
            end_time=now - datetime.timedelta(days=1) + datetime.timedelta(hours=1),
            rrule="FREQ=DAILY;COUNT=5",
        )
        db_session.add(event)
        await db_session.commit()

        start = urllib.parse.quote((now - datetime.timedelta(days=2)).isoformat())
        end = urllib.parse.quote((now + datetime.timedelta(days=10)).isoformat())
        resp = await client.get(f"/api/calendar/events?start={start}&end={end}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert len(data) > 1

    @pytest.mark.asyncio
    async def test_update_event_rrule(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        now = _utcnow()
        event = CalendarEvent(
            account_id=acct.id, provider_event_id="mock-upd-1",
            title="Test", start_time=now, end_time=now + datetime.timedelta(hours=1),
        )
        db_session.add(event)
        await db_session.commit()
        await db_session.refresh(event)

        resp = await client.put(f"/api/calendar/events/{event.id}", json={
            "rrule": "FREQ=WEEKLY;COUNT=5",
        })
        assert resp.status_code == 200
        assert resp.json()["rrule"] == "FREQ=WEEKLY;COUNT=5"

    @pytest.mark.asyncio
    async def test_invalid_rrule_returns_400(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        now = _utcnow()
        resp = await client.post("/api/calendar/events", json={
            "account_id": acct.id, "title": "Bad",
            "start_time": now.isoformat(), "end_time": (now + datetime.timedelta(hours=1)).isoformat(),
            "rrule": "FREQ=BIWEEKLY",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_events_with_rrule_badge(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        now = _utcnow()
        event = CalendarEvent(
            account_id=acct.id, provider_event_id="mock-badge-1",
            title="Weekly Meeting", category="meeting",
            start_time=now, end_time=now + datetime.timedelta(hours=1),
            rrule="FREQ=WEEKLY;COUNT=10",
        )
        db_session.add(event)
        await db_session.commit()

        start = urllib.parse.quote(now.isoformat())
        end = urllib.parse.quote((now + datetime.timedelta(days=30)).isoformat())
        resp = await client.get(f"/api/calendar/events?start={start}&end={end}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        for evt in data:
            if evt["id"] == event.id:
                assert evt["rrule"] is not None
                break
