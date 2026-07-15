import pytest
from app.automation.actions import execute_action, ACTION_HANDLERS
from app.automation.engine import _matches_trigger


class TestActions:
    def test_auto_reply_action(self):
        result = execute_action("test_rule", "auto_reply", {"subject": "Re: Hello", "body": "Thanks!"}, {"subject": "Hello"})
        assert result["action"] == "auto_reply"
        assert "Thanks!" in result["body"]

    def test_categorize_action(self):
        result = execute_action("test", "categorize", {"category": "urgent"})
        assert result["action"] == "categorize"
        assert result["category"] == "urgent"

    def test_mark_read_action(self):
        result = execute_action("test", "mark_read", {})
        assert result["action"] == "mark_read"

    def test_star_action(self):
        result = execute_action("test", "star", {})
        assert result["action"] == "star"

    def test_forward_action(self):
        result = execute_action("test", "forward", {"to": "user@example.com"})
        assert result["action"] == "forward"
        assert result["to"] == "user@example.com"

    def test_unknown_action(self):
        result = execute_action("test", "nonexistent", {})
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

    def test_list_match(self):
        assert _matches_trigger({"folder": ["INBOX", "IMPORTANT"]}, {"folder": "INBOX"}) is True

    def test_list_no_match(self):
        assert _matches_trigger({"folder": ["INBOX"]}, {"folder": "SENT"}) is False

    def test_regex_match(self):
        assert _matches_trigger({"subject": "re:meeting"}, {"subject": "Meeting tomorrow at 3pm"}) is True

    def test_regex_no_match(self):
        assert _matches_trigger({"subject": "re:urgent"}, {"subject": "Just a friendly hello"}) is False

    def test_multiple_conditions_all_match(self):
        assert _matches_trigger(
            {"folder": "INBOX", "from": "boss@co.com"},
            {"folder": "INBOX", "from": "boss@co.com"},
        ) is True

    def test_multiple_conditions_one_fails(self):
        assert _matches_trigger(
            {"folder": "INBOX", "from": "boss@co.com"},
            {"folder": "INBOX", "from": "spam@spam.com"},
        ) is False

    def test_empty_config_matches_anything(self):
        assert _matches_trigger({}, {"anything": "goes"}) is True


class TestAutomationAPICRUD:
    @pytest.mark.asyncio
    async def test_list_trigger_types(self, client):
        resp = await client.get("/api/automation/trigger-types")
        assert resp.status_code == 200
        assert "new_email" in resp.json()
        assert "cron_schedule" in resp.json()

    @pytest.mark.asyncio
    async def test_list_action_types(self, client):
        resp = await client.get("/api/automation/action-types")
        assert resp.status_code == 200
        assert "auto_reply" in resp.json()
        assert "forward" in resp.json()

    @pytest.mark.asyncio
    async def test_create_and_list_rules(self, client):
        payload = {
            "name": "Test Rule",
            "description": "A test rule",
            "trigger_type": "new_email",
            "trigger_config": {"folder": "INBOX"},
            "action_type": "mark_read",
            "action_config": {},
            "is_enabled": True,
        }
        create = await client.post("/api/automation/rules", json=payload)
        assert create.status_code == 200
        data = create.json()
        assert data["name"] == "Test Rule"
        assert data["trigger_type"] == "new_email"
        assert data["is_enabled"] is True

        lst = await client.get("/api/automation/rules")
        assert lst.status_code == 200
        assert len(lst.json()) == 1

    @pytest.mark.asyncio
    async def test_create_cron_rule_without_schedule_returns_400(self, client):
        resp = await client.post("/api/automation/rules", json={
            "name": "Bad Cron",
            "trigger_type": "cron_schedule",
            "action_type": "auto_reply",
            "action_config": {"body": "Hi"},
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_rule_with_valid_cron(self, client):
        resp = await client.post("/api/automation/rules", json={
            "name": "Cron Rule",
            "trigger_type": "cron_schedule",
            "action_type": "auto_reply",
            "action_config": {"body": "Auto reply"},
            "cron_schedule": "*/5 * * * *",
            "is_enabled": True,
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_rule(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Original", "trigger_type": "new_email", "action_type": "star",
        })
        rule_id = created.json()["id"]
        updated = await client.put(f"/api/automation/rules/{rule_id}", json={
            "name": "Updated", "is_enabled": False,
        })
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated"
        assert updated.json()["is_enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_rule(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Togglable", "trigger_type": "new_email", "action_type": "star",
        })
        rule_id = created.json()["id"]
        was_enabled = created.json()["is_enabled"]

        toggled = await client.post(f"/api/automation/rules/{rule_id}/toggle")
        assert toggled.json()["is_enabled"] is not was_enabled

    @pytest.mark.asyncio
    async def test_delete_rule(self, client):
        created = await client.post("/api/automation/rules", json={
            "name": "Delete Me", "trigger_type": "new_email", "action_type": "star",
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
