import datetime
import pytest
from sqlalchemy import select
from app.models import EmailAccount, Email, Folder, ProviderType


class TestFolderAPI:
    @pytest.mark.asyncio
    async def test_list_folders_includes_system(self, client):
        resp = await client.get("/api/folders")
        assert resp.status_code == 200
        data = resp.json()
        names = [f["name"] for f in data]
        assert "INBOX" in names
        assert "SENT" in names
        assert "DRAFTS" in names
        assert "STARRED" in names

    @pytest.mark.asyncio
    async def test_create_custom_folder(self, client):
        resp = await client.post("/api/folders", json={"name": "Projects", "color": "blue", "icon": "briefcase"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Projects"
        assert data["normalized_name"] == "PROJECTS"
        assert data["is_system"] is False

    @pytest.mark.asyncio
    async def test_create_duplicate_folder_returns_409(self, client):
        await client.post("/api/folders", json={"name": "Projects"})
        resp = await client.post("/api/folders", json={"name": "projects"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_update_folder(self, client):
        create = await client.post("/api/folders", json={"name": "Old Name"})
        folder_id = create.json()["id"]
        resp = await client.put(f"/api/folders/{folder_id}", json={"name": "New Name", "color": "red"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["normalized_name"] == "NEW NAME"
        assert resp.json()["color"] == "red"

    @pytest.mark.asyncio
    async def test_delete_folder_moves_emails_to_inbox(self, client, db_session):
        acct = EmailAccount(email="f@f.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        folder = Folder(name="Temp", normalized_name="TEMP", color="blue", icon="folder", is_system=False)
        db_session.add(folder)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="temp1",
            from_address="a@b.com", to_addresses="f@f.com",
            subject="In temp", folder="TEMP", is_read=True,
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        resp = await client.delete(f"/api/folders/{folder.id}")
        assert resp.status_code == 200

        # Refresh email from DB
        result = await db_session.execute(select(Email).where(Email.id == email.id))
        refreshed = result.scalar_one()
        assert refreshed.folder == "INBOX"
        assert refreshed.is_read is False

    @pytest.mark.asyncio
    async def test_delete_system_folder_returns_400(self, client, db_session):
        inbox = await db_session.execute(select(Folder).where(Folder.normalized_name == "INBOX"))
        inbox = inbox.scalar_one()
        resp = await client.delete(f"/api/folders/{inbox.id}")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_email_move_to_custom_folder(self, client, db_session):
        acct = EmailAccount(email="mv2@mv2.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        folder = Folder(name="Receipts", normalized_name="RECEIPTS", color="emerald", icon="tag", is_system=False)
        db_session.add(folder)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="mv2",
            from_address="a@b.com", to_addresses="mv2@mv2.com",
            subject="Move to custom", folder="INBOX",
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        resp = await client.post(f"/api/emails/{email.id}/move", json={"folder": "RECEIPTS"})
        assert resp.status_code == 200
        assert resp.json()["folder"] == "RECEIPTS"

    @pytest.mark.asyncio
    async def test_list_emails_in_custom_folder(self, client, db_session):
        acct = EmailAccount(email="lst@lst.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        folder = Folder(name="Newsletters", normalized_name="NEWSLETTERS", color="violet", icon="document", is_system=False)
        db_session.add(folder)
        await db_session.commit()

        db_session.add_all([
            Email(account_id=acct.id, provider_message_id="n1", from_address="a@b.com", to_addresses="lst@lst.com",
                  subject="Newsletter 1", folder="NEWSLETTERS", received_at=datetime.datetime.now(datetime.UTC)),
            Email(account_id=acct.id, provider_message_id="n2", from_address="c@d.com", to_addresses="lst@lst.com",
                  subject="Other", folder="INBOX", received_at=datetime.datetime.now(datetime.UTC)),
        ])
        await db_session.commit()

        resp = await client.get("/api/emails?folder=NEWSLETTERS")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Newsletter 1"
