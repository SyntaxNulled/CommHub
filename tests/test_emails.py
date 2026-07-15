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
    async def test_get_email_does_not_mutate_read_state(self, client, db_session):
        """GET must be safe — read state changes only via the explicit mark-read endpoint."""
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
        assert resp.json()["is_read"] is False

        mark = await client.post(f"/api/emails/{email.id}/mark-read")
        assert mark.status_code == 200
        assert mark.json()["is_read"] is True

        resp2 = await client.get(f"/api/emails/{email.id}")
        assert resp2.json()["is_read"] is True

    @pytest.mark.asyncio
    async def test_unknown_folder_returns_400(self, client):
        resp = await client.get("/api/emails?folder=TRASH")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unread_count(self, client, db_session):
        acct = EmailAccount(email="uc@uc.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        for i, read in enumerate([False, False, True]):
            db_session.add(Email(
                account_id=acct.id, provider_message_id=f"uc-{i}",
                from_address="a@b.com", to_addresses="uc@uc.com",
                subject=f"E{i}", folder="INBOX", is_read=read,
                received_at=datetime.datetime.now(datetime.UTC),
            ))
        await db_session.commit()

        resp = await client.get("/api/emails/unread-count")
        assert resp.status_code == 200
        assert resp.json()["unread"] == 2

    @pytest.mark.asyncio
    async def test_server_side_search(self, client, db_session):
        acct = EmailAccount(email="s@s.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        db_session.add_all([
            Email(account_id=acct.id, provider_message_id="s-1",
                  from_address="alice@x.com", to_addresses="s@s.com",
                  subject="Quarterly report", body_text="numbers inside",
                  folder="INBOX", received_at=datetime.datetime.now(datetime.UTC)),
            Email(account_id=acct.id, provider_message_id="s-2",
                  from_address="bob@x.com", to_addresses="s@s.com",
                  subject="Lunch plans", body_text="pizza?",
                  folder="INBOX", received_at=datetime.datetime.now(datetime.UTC)),
        ])
        await db_session.commit()

        resp = await client.get("/api/emails?folder=INBOX&q=quarterly")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["subject"] == "Quarterly report"
        assert resp.headers["X-Total-Count"] == "1"

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
        assert resp.status_code == 201
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
        assert resp.status_code == 201
        assert resp.json()["folder"] == "DRAFTS"

    @pytest.mark.asyncio
    async def test_send_email_without_recipient_returns_400(self, client, db_session):
        acct = EmailAccount(email="nr@nr.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        resp = await client.post("/api/emails/send", json={
            "account_id": acct.id, "to": "   ", "subject": "No recipient", "body": "x",
        })
        assert resp.status_code == 400

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

    @pytest.mark.asyncio
    async def test_pagination(self, client, db_session):
        acct = EmailAccount(email="p@p.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        for i in range(5):
            db_session.add(Email(account_id=acct.id, provider_message_id=f"pg-{i}",
                                 from_address="a@b.com", to_addresses="p@p.com",
                                 subject=f"Page test {i}", folder="INBOX",
                                 received_at=datetime.datetime.now(datetime.UTC)))
        await db_session.commit()

        resp = await client.get("/api/emails?folder=INBOX&page=1&page_size=2")
        assert resp.status_code == 200
        assert resp.headers.get("X-Total-Count") == "5"
        assert len(resp.json()) == 2

        resp2 = await client.get("/api/emails?folder=INBOX&page=2&page_size=2")
        assert resp2.headers.get("X-Total-Count") == "5"
        assert len(resp2.json()) == 2

        resp3 = await client.get("/api/emails?folder=INBOX&page=3&page_size=2")
        assert len(resp3.json()) == 1

    @pytest.mark.asyncio
    async def test_move_email(self, client, db_session):
        acct = EmailAccount(email="mv@mv.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        email = Email(account_id=acct.id, provider_message_id="mv",
                      from_address="a@b.com", to_addresses="mv@mv.com",
                      subject="Move me", folder="INBOX", is_read=True,
                      received_at=datetime.datetime.now(datetime.UTC))
        db_session.add(email)
        await db_session.commit()

        resp = await client.post(f"/api/emails/{email.id}/move", json={"folder": "SENT"})
        assert resp.status_code == 200
        assert resp.json()["folder"] == "SENT"

        # Moving back to INBOX resets read state
        resp2 = await client.post(f"/api/emails/{email.id}/move", json={"folder": "INBOX"})
        assert resp2.status_code == 200
        assert resp2.json()["folder"] == "INBOX"
        get_resp = await client.get(f"/api/emails/{email.id}")
        assert get_resp.json()["is_read"] is False

    @pytest.mark.asyncio
    async def test_move_email_unknown_folder_returns_400(self, client, db_session):
        acct = EmailAccount(email="bad@bad.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()
        import datetime
        email = Email(account_id=acct.id, provider_message_id="bad",
                      from_address="a@b.com", to_addresses="bad@bad.com",
                      subject="Bad folder", folder="INBOX",
                      received_at=datetime.datetime.now(datetime.UTC))
        db_session.add(email)
        await db_session.commit()

        resp = await client.post(f"/api/emails/{email.id}/move", json={"folder": "TRASH"})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_move_email_nonexistent_returns_404(self, client):
        resp = await client.post("/api/emails/99999/move", json={"folder": "SENT"})
        assert resp.status_code == 404
