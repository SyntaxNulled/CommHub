import pytest
from sqlalchemy import select
from app.models import EmailAccount, Email, ProviderType


class TestEmailAPI:
    @pytest.mark.asyncio
    async def test_list_emails_empty(self, client, db_session):
        resp = await client.get("/api/emails?folder=INBOX")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_and_list_email(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL, display_name="Test")
        db_session.add(acct)
        await db_session.commit()

        import datetime
        email = Email(
            account_id=acct.id, provider_message_id="test-1",
            from_address="sender@test.com", from_name="Sender",
            to_addresses="test@test.com", subject="Hello World",
            body_text="This is a test email", folder="INBOX",
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        resp = await client.get("/api/emails?folder=INBOX")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Hello World"
        assert data[0]["is_read"] is False

    @pytest.mark.asyncio
    async def test_get_email_marks_as_read(self, client, db_session):
        acct = EmailAccount(email="test@test.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        email = Email(
            account_id=acct.id, provider_message_id="test-2",
            from_address="a@b.com", to_addresses="test@test.com",
            subject="Unread", body_text="Body", folder="INBOX",
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        resp = await client.get(f"/api/emails/{email.id}")
        assert resp.status_code == 200
        assert resp.json()["is_read"] is True

    @pytest.mark.asyncio
    async def test_toggle_star(self, client, db_session):
        acct = EmailAccount(email="t@t.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        email = Email(account_id=acct.id, provider_message_id="t3",
                      from_address="a@b.com", to_addresses="t@t.com",
                      subject="S", folder="INBOX",
                      received_at=datetime.datetime.now(datetime.UTC))
        db_session.add(email)
        await db_session.commit()

        resp = await client.post(f"/api/emails/{email.id}/toggle-star")
        assert resp.json()["is_starred"] is True
        resp2 = await client.post(f"/api/emails/{email.id}/toggle-star")
        assert resp2.json()["is_starred"] is False

    @pytest.mark.asyncio
    async def test_send_email(self, client, db_session):
        acct = EmailAccount(email="me@me.com", provider=ProviderType.GMAIL, display_name="Me")
        db_session.add(acct)
        await db_session.commit()

        resp = await client.post("/api/emails/send", json={
            "account_id": acct.id, "to": "you@you.com",
            "subject": "Test Send", "body": "Hello!",
        })
        assert resp.status_code == 200
        assert resp.json()["folder"] == "SENT"
        assert resp.json()["subject"] == "Test Send"

    @pytest.mark.asyncio
    async def test_save_draft(self, client, db_session):
        acct = EmailAccount(email="me@me.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        resp = await client.post("/api/emails/draft", json={
            "account_id": acct.id, "to": "", "subject": "Draft", "body": "WIP",
        })
        assert resp.status_code == 200
        assert resp.json()["folder"] == "DRAFTS"

    @pytest.mark.asyncio
    async def test_delete_email(self, client, db_session):
        acct = EmailAccount(email="t@t.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        email = Email(account_id=acct.id, provider_message_id="del",
                      from_address="a@b.com", to_addresses="t@t.com",
                      subject="Delete me", folder="INBOX",
                      received_at=datetime.datetime.now(datetime.UTC))
        db_session.add(email)
        await db_session.commit()

        resp = await client.delete(f"/api/emails/{email.id}")
        assert resp.status_code == 200
        resp2 = await client.get(f"/api/emails/{email.id}")
        assert resp2.status_code == 404

    @pytest.mark.asyncio
    async def test_list_sent_folder(self, client, db_session):
        acct = EmailAccount(email="x@x.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        for fld in ["SENT", "DRAFTS", "INBOX"]:
            db_session.add(Email(account_id=acct.id, provider_message_id=f"f-{fld}",
                                 from_address="a@b.com", to_addresses="x@x.com",
                                 subject=fld, folder=fld,
                                 received_at=datetime.datetime.now(datetime.UTC)))
        await db_session.commit()

        sent = await client.get("/api/emails?folder=SENT")
        assert len(sent.json()) == 1
        assert sent.json()[0]["folder"] == "SENT"

        inbox = await client.get("/api/emails?folder=INBOX")
        assert len(inbox.json()) == 1
