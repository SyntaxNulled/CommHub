import datetime
import pytest
from sqlalchemy import select
from app.models import Email, EmailAccount, ProviderType


class TestEmailSnooze:
    @pytest.mark.asyncio
    async def test_snooze_email(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mock-1",
            from_address="from@test.com", to_addresses="to@test.com",
            subject="Test", body_text="Body", folder="INBOX",
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        until = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        resp = await client.post(f"/api/emails/{email.id}/snooze", json={"until": until.isoformat()})
        assert resp.status_code == 200
        data = resp.json()
        assert data["snoozed_until"] is not None

    @pytest.mark.asyncio
    async def test_snooze_email_not_found_returns_404(self, client):
        resp = await client.post("/api/emails/999/snooze", json={"until": "2026-12-31T23:59:00"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unsnooze_email(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mock-2",
            from_address="from@test.com", to_addresses="to@test.com",
            subject="Test", body_text="Body", folder="INBOX",
            snoozed_until=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        resp = await client.post(f"/api/emails/{email.id}/unsnooze")
        assert resp.status_code == 200
        assert resp.json()["snoozed_until"] is None

    @pytest.mark.asyncio
    async def test_snoozed_emails_excluded_from_inbox(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email1 = Email(
            account_id=acct.id, provider_message_id="mock-3",
            from_address="a@test.com", to_addresses="to@test.com",
            subject="Normal", body_text="Body", folder="INBOX",
            received_at=datetime.datetime.now(datetime.UTC),
        )
        email2 = Email(
            account_id=acct.id, provider_message_id="mock-4",
            from_address="b@test.com", to_addresses="to@test.com",
            subject="Snoozed", body_text="Body", folder="INBOX",
            snoozed_until=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add_all([email1, email2])
        await db_session.commit()

        resp = await client.get("/api/emails?folder=INBOX")
        assert resp.status_code == 200
        subjects = [e["subject"] for e in resp.json()]
        assert "Normal" in subjects
        assert "Snoozed" not in subjects

    @pytest.mark.asyncio
    async def test_snoozed_emails_listed_in_snoozed_folder(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mock-5",
            from_address="a@test.com", to_addresses="to@test.com",
            subject="Snoozed One", body_text="Body", folder="INBOX",
            snoozed_until=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        resp = await client.get("/api/emails?folder=SNOOZED")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Snoozed One"

    @pytest.mark.asyncio
    async def test_undo_send_deletes_email(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mock-6",
            from_address="from@test.com", to_addresses="to@test.com",
            subject="Pending", body_text="Body", folder="SENT",
            send_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=10),
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        resp = await client.post(f"/api/emails/{email.id}/undo-send")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == email.id

        result = await db_session.execute(select(Email).where(Email.id == email.id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_undo_send_no_pending_returns_400(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mock-7",
            from_address="from@test.com", to_addresses="to@test.com",
            subject="Sent", body_text="Body", folder="SENT",
            send_at=None,
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()
        await db_session.refresh(email)

        resp = await client.post(f"/api/emails/{email.id}/undo-send")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sent_email_has_send_at(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        now = datetime.datetime.now(datetime.UTC)
        resp = await client.post("/api/emails/send", json={
            "account_id": acct.id, "to": "recipient@test.com",
            "subject": "Hello", "body": "World",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["send_at"] is not None

    @pytest.mark.asyncio
    async def test_pending_send_excluded_from_list(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mock-8",
            from_address="from@test.com", to_addresses="to@test.com",
            subject="Pending Send", body_text="Body", folder="SENT",
            send_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=10),
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        resp = await client.get("/api/emails?folder=SENT")
        assert resp.status_code == 200
        subjects = [e["subject"] for e in resp.json()]
        assert "Pending Send" not in subjects
