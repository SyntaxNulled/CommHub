import datetime
import pytest
from app.automation.actions import execute_action, ACTION_HANDLERS
from app.automation.engine import _matches_trigger
from app.routers.ai import get_active_provider, ActiveProviderInfo
from app.ai.providers.mock import MockProvider
from app.ai.providers.base import AIProviderConfig


class TestActions:
    @pytest.mark.asyncio
    async def test_auto_reply_action(self):
        result = await execute_action("test_rule", "auto_reply", {"subject": "Re: Hello", "body": "Thanks!"}, {"subject": "Hello"})
        assert result["action"] == "auto_reply"
        assert "Thanks!" in result["body"]

    @pytest.mark.asyncio
    async def test_categorize_action(self):
        result = await execute_action("test", "categorize", {"category": "urgent"})
        assert result["action"] == "categorize"
        assert result["category"] == "urgent"

    @pytest.mark.asyncio
    async def test_mark_read_action(self):
        result = await execute_action("test", "mark_read", {})
        assert result["action"] == "mark_read"

    @pytest.mark.asyncio
    async def test_star_action(self):
        result = await execute_action("test", "star", {})
        assert result["action"] == "star"

    @pytest.mark.asyncio
    async def test_forward_action(self):
        result = await execute_action("test", "forward", {"to": "user@example.com"})
        assert result["action"] == "forward"
        assert result["to"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        result = await execute_action("test", "nonexistent", {})
        assert result["action"] == "unknown"

    def test_all_actions_have_handlers(self):
        from app.routers.automation import ACTION_TYPES
        for action in ACTION_TYPES:
            assert action in ACTION_HANDLERS, f"Missing handler for {action}"


class TestTriggerMatching:
    def test_exact_match(self):
        assert _matches_trigger({"subject": "Hello"}, {"subject": "Hello"}) is True

    def test_mismatch(self):
        assert _matches_trigger({"subject": "Hello"}, {"subject": "World"}) is False

    def test_regex_match(self):
        assert _matches_trigger({"subject": "re:invoice.*"}, {"subject": "re:invoice"}) is True

    def test_list_match(self):
        assert _matches_trigger({"from": ["a@b.com", "c@d.com"]}, {"from": "a@b.com"}) is True

    def test_regex_invalid_returns_false(self):
        assert _matches_trigger({"subject": "re:[bad"}, {"subject": "Hello"}) is False


class TestAutomationAPI:
    @pytest.mark.asyncio
    async def test_list_trigger_types(self, client):
        resp = await client.get("/api/automation/trigger-types")
        assert resp.status_code == 200
        assert "new_email" in resp.json()

    @pytest.mark.asyncio
    async def test_list_action_types(self, client):
        resp = await client.get("/api/automation/action-types")
        assert resp.status_code == 200
        assert "ai_categorize" in resp.json()

    @pytest.mark.asyncio
    async def test_create_and_list_rules(self, client):
        payload = {
            "name": "Test Rule", "trigger_type": "new_email", "action_type": "mark_read",
            "trigger_config": {"subject": "Alert"},
        }
        create = await client.post("/api/automation/rules", json=payload)
        assert create.status_code == 201
        lst = await client.get("/api/automation/rules")
        assert len(lst.json()) == 1

    @pytest.mark.asyncio
    async def test_create_cron_rule_without_schedule_returns_400(self, client):
        resp = await client.post("/api/automation/rules", json={
            "name": "Bad", "trigger_type": "cron_schedule", "action_type": "mark_read",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_rule_with_valid_cron(self, client):
        resp = await client.post("/api/automation/rules", json={
            "name": "Cron", "trigger_type": "cron_schedule", "action_type": "mark_read",
            "cron_schedule": "*/5 * * * *",
        })
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_rule_with_invalid_cron_returns_400(self, client):
        resp = await client.post("/api/automation/rules", json={
            "name": "Bad", "trigger_type": "cron_schedule", "action_type": "mark_read",
            "cron_schedule": "not-a-cron",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_rule_cannot_create_invalid_state(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Ok", "trigger_type": "new_email", "action_type": "mark_read",
        })
        rule_id = created.json()["id"]
        resp = await client.put(f"/api/automation/rules/{rule_id}", json={
            "trigger_type": "cron_schedule",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_rule_with_invalid_regex_returns_400(self, client):
        resp = await client.post("/api/automation/rules", json={
            "name": "Bad", "trigger_type": "new_email", "action_type": "mark_read",
            "trigger_config": {"subject": "re:[bad"},
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_update_rule(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Original", "trigger_type": "new_email", "action_type": "mark_read",
        })
        rule_id = created.json()["id"]
        updated = await client.put(f"/api/automation/rules/{rule_id}", json={
            "name": "Updated", "action_type": "star",
        })
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated"
        assert updated.json()["action_type"] == "star"

    @pytest.mark.asyncio
    async def test_toggle_rule(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Toggle", "trigger_type": "new_email", "action_type": "mark_read",
        })
        rule_id = created.json()["id"]
        toggled = await client.post(f"/api/automation/rules/{rule_id}/toggle")
        assert toggled.status_code == 200
        assert toggled.json()["is_enabled"] is False

    @pytest.mark.asyncio
    async def test_delete_rule(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Delete", "trigger_type": "new_email", "action_type": "mark_read",
        })
        rule_id = created.json()["id"]
        del_resp = await client.delete(f"/api/automation/rules/{rule_id}")
        assert del_resp.status_code == 200
        lst = await client.get("/api/automation/rules")
        assert len(lst.json()) == 0

    @pytest.mark.asyncio
    async def test_scheduler_jobs_list(self, client):
        resp = await client.get("/api/automation/scheduler/jobs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_ai_categorize_rule(self, client, db_session, mock_provider_override):
        from app.models import Email, EmailAccount, ProviderType
        acct = EmailAccount(email="ai@ai.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        email = Email(
            account_id=acct.id, provider_message_id="ai1",
            from_address="invoice@example.com", to_addresses=acct.email,
            subject="Invoice #123", body_text="Please pay invoice 123", folder="INBOX",
            received_at=datetime.datetime.now(datetime.UTC),
        )
        db_session.add(email)
        await db_session.commit()

        rule = await client.post("/api/automation/rules", json={
            "name": "AI Sort", "trigger_type": "new_email", "action_type": "ai_categorize",
            "action_config": {"fallback_folder": "INBOX"},
        })
        assert rule.status_code == 201

        results = await client.post("/api/automation/test-trigger", params={"trigger_type": "new_email"})
        assert results.status_code == 200



@pytest.fixture
def mock_provider_override():
    from app.main import app as _app
    mock_provider_info = ActiveProviderInfo(
        provider=MockProvider(AIProviderConfig()),
        provider_type="mock",
        model="mock-v1",
    )

    async def override():
        return mock_provider_info

    _app.dependency_overrides[get_active_provider] = override
    yield
    _app.dependency_overrides.clear()
