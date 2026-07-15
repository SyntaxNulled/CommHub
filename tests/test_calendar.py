import pytest
import datetime


class TestCalendarAPI:
    @pytest.mark.asyncio
    async def test_list_events_empty(self, client):
        resp = await client.get("/api/calendar/events")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_event(self, client, db_session):
        from app.models import CalendarEvent, EmailAccount, ProviderType
        from sqlalchemy import select

        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        resp = await client.post("/api/calendar/events", json={
            "account_id": acct.id,
            "title": "Team Standup",
            "description": "Daily standup",
            "start_time": "2026-07-16T09:00:00",
            "end_time": "2026-07-16T09:30:00",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Team Standup"
        assert data["description"] == "Daily standup"
        assert "2026-07-16T09:00:00" in data["start_time"]

    @pytest.mark.asyncio
    async def test_create_event_end_before_start_returns_400(self, client, db_session):
        from app.models import EmailAccount, ProviderType
        acct = EmailAccount(email="rev@rev.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        resp = await client.post("/api/calendar/events", json={
            "account_id": acct.id,
            "title": "Backwards",
            "start_time": "2026-07-16T10:00:00",
            "end_time": "2026-07-16T09:00:00",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_events_invalid_date_filter_returns_400(self, client):
        resp = await client.get("/api/calendar/events?start=not-a-date")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_events_with_date_filter(self, client, db_session):
        from app.models import CalendarEvent, EmailAccount, ProviderType
        from sqlalchemy import select

        acct = EmailAccount(email="t@t.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        db_session.add_all([
            CalendarEvent(account_id=acct.id, provider_event_id="e1",
                          title="Event 1",
                          start_time=datetime.datetime(2026, 7, 16, 10, 0),
                          end_time=datetime.datetime(2026, 7, 16, 11, 0)),
            CalendarEvent(account_id=acct.id, provider_event_id="e2",
                          title="Event 2",
                          start_time=datetime.datetime(2026, 7, 20, 14, 0),
                          end_time=datetime.datetime(2026, 7, 20, 15, 0)),
        ])
        await db_session.commit()

        resp = await client.get("/api/calendar/events?start=2026-07-15T00:00:00&end=2026-07-18T00:00:00")
        titles = [e["title"] for e in resp.json()]
        assert "Event 1" in titles
        assert "Event 2" not in titles

    @pytest.mark.asyncio
    async def test_update_event(self, client, db_session):
        from app.models import CalendarEvent, EmailAccount, ProviderType
        acct = EmailAccount(email="u@u.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        evt = CalendarEvent(account_id=acct.id, provider_event_id="upd",
                            title="Original", description="",
                            start_time=datetime.datetime(2026, 7, 16, 12, 0),
                            end_time=datetime.datetime(2026, 7, 16, 13, 0))
        db_session.add(evt)
        await db_session.commit()

        resp = await client.put(f"/api/calendar/events/{evt.id}", json={
            "title": "Updated", "description": "New desc",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["description"] == "New desc"

    @pytest.mark.asyncio
    async def test_delete_event(self, client, db_session):
        from app.models import CalendarEvent, EmailAccount, ProviderType
        acct = EmailAccount(email="d@d.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        evt = CalendarEvent(account_id=acct.id, provider_event_id="del",
                            title="Delete me",
                            start_time=datetime.datetime(2026, 7, 16, 12, 0),
                            end_time=datetime.datetime(2026, 7, 16, 13, 0))
        db_session.add(evt)
        await db_session.commit()

        resp = await client.delete(f"/api/calendar/events/{evt.id}")
        assert resp.status_code == 200
        resp2 = await client.get("/api/calendar/events")
        assert len(resp2.json()) == 0

    @pytest.mark.asyncio
    async def test_create_event_invalid_date_returns_400(self, client):
        resp = await client.post("/api/calendar/events", json={
            "title": "Bad", "start_time": "not-a-date", "end_time": "also-not",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_seed_endpoint(self, client):
        resp = await client.post("/api/seed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("seeded", "already_seeded")
        if data["status"] == "seeded":
            assert data["emails"] > 0
            assert data["events"] > 0
