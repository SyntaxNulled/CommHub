import datetime
import pytest
from app.ai.providers import get_provider, PROVIDER_REGISTRY
from app.ai.providers.base import AIProviderConfig
from app.ai.providers.mock import MockProvider
from app.routers.ai import ActiveProviderInfo, get_active_provider


class TestProviderRegistry:
    def test_registry_contains_expected_providers(self):
        assert "openai" in PROVIDER_REGISTRY
        assert "anthropic" in PROVIDER_REGISTRY
        assert "ollama" in PROVIDER_REGISTRY
        assert "custom" in PROVIDER_REGISTRY

    def test_get_provider_raises_for_unknown(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")

    def test_custom_provider_uses_openai_class(self):
        assert PROVIDER_REGISTRY["custom"] is PROVIDER_REGISTRY["openai"]


class TestMockProvider:
    @pytest.fixture
    def provider(self):
        return MockProvider(AIProviderConfig())

    @pytest.mark.asyncio
    async def test_draft_reply(self, provider):
        result = await provider.draft_reply("Hello, this is a test email", tone="friendly")
        assert result.startswith("[Mock friendly draft reply")

    @pytest.mark.asyncio
    async def test_summarize(self, provider):
        result = await provider.summarize_email("Long email body here " * 10)
        assert "Mock summary" in result

    @pytest.mark.asyncio
    async def test_categorize(self, provider):
        result = await provider.categorize_email("Meeting tomorrow", "Please join")
        assert result == "work"

    @pytest.mark.asyncio
    async def test_generate_response(self, provider):
        result = await provider.generate_response("What is the weather?")
        assert result.startswith("[Mock response")


class TestAIProviderConfigCRUD:
    @pytest.mark.asyncio
    async def test_list_available_providers(self, client):
        response = await client.get("/api/ai/providers")
        assert response.status_code == 200
        providers = response.json()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
        assert "custom" in providers

    @pytest.mark.asyncio
    async def test_create_and_list_config(self, client):
        payload = {
            "provider_type": "openai",
            "display_name": "My OpenAI",
            "api_key": "sk-test123",
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 2048,
        }
        create_resp = await client.post("/api/ai/configs", json=payload)
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert data["provider_type"] == "openai"
        assert data["display_name"] == "My OpenAI"
        assert data["is_active"] is False
        # Secret must never be echoed back
        assert "api_key" not in data
        assert data["has_api_key"] is True
        assert data["api_key_masked"].startswith("sk-")
        assert "test123" not in data["api_key_masked"]

        list_resp = await client.get("/api/ai/configs")
        assert list_resp.status_code == 200
        configs = list_resp.json()
        assert len(configs) == 1
        assert configs[0]["provider_type"] == "openai"
        assert "api_key" not in configs[0]

    @pytest.mark.asyncio
    async def test_create_duplicate_builtin_provider_returns_409(self, client):
        payload = {"provider_type": "openai", "display_name": "Test", "api_key": "sk-test"}
        await client.post("/api/ai/configs", json=payload)
        resp = await client.post("/api/ai/configs", json=payload)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_multiple_custom_providers_allowed(self, client):
        for i in range(3):
            resp = await client.post("/api/ai/configs", json={
                "provider_type": "custom",
                "display_name": f"Custom {i}",
                "base_url": f"https://api{i}.example.com/v1",
                "model": f"model-{i}",
                "api_key": "sk-test",
            })
            assert resp.status_code == 201, f"Failed creating custom provider {i}: {resp.json()}"
        list_resp = await client.get("/api/ai/configs")
        assert len(list_resp.json()) == 3

    @pytest.mark.asyncio
    async def test_create_unknown_provider_returns_400(self, client):
        resp = await client.post("/api/ai/configs", json={
            "provider_type": "skynet", "display_name": "Nope",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_activating_provider_deactivates_others(self, client):
        r1 = await client.post("/api/ai/configs", json={"provider_type": "openai", "display_name": "A"})
        r2 = await client.post("/api/ai/configs", json={"provider_type": "anthropic", "display_name": "B"})
        await client.put(f"/api/ai/configs/{r1.json()['id']}", json={"is_active": True})
        await client.put(f"/api/ai/configs/{r2.json()['id']}", json={"is_active": True})

        configs = (await client.get("/api/ai/configs")).json()
        active = [c for c in configs if c["is_active"]]
        assert len(active) == 1
        assert active[0]["provider_type"] == "anthropic"

    @pytest.mark.asyncio
    async def test_update_config(self, client):
        create = await client.post("/api/ai/configs", json={
            "provider_type": "anthropic", "display_name": "Claude", "api_key": "sk-ant-test",
        })
        config_id = create.json()["id"]
        update_resp = await client.put(f"/api/ai/configs/{config_id}", json={
            "display_name": "Claude Updated", "model": "claude-opus-4", "is_active": True,
        })
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["display_name"] == "Claude Updated"
        assert data["model"] == "claude-opus-4"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, client):
        resp = await client.put("/api/ai/configs/99999", json={"display_name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_config(self, client):
        create = await client.post("/api/ai/configs", json={
            "provider_type": "ollama", "display_name": "Local LLM", "api_key": "",
        })
        config_id = create.json()["id"]
        del_resp = await client.delete(f"/api/ai/configs/{config_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] == config_id
        list_resp = await client.get("/api/ai/configs")
        assert len(list_resp.json()) == 0


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


class TestAIEndpointsWithMock:
    @pytest.mark.asyncio
    async def test_draft_endpoint(self, client, mock_provider_override):
        resp = await client.post("/api/ai/draft", json={
            "email_text": "Can you send me the report?",
            "tone": "professional",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "mock"
        assert data["model"] == "mock-v1"
        assert "[Mock" in data["result"]

    @pytest.mark.asyncio
    async def test_chat_endpoint(self, client, mock_provider_override):
        resp = await client.post("/api/ai/chat", json={"prompt": "Hello!"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "mock"

    @pytest.mark.asyncio
    async def test_summarize_endpoint(self, client, mock_provider_override):
        resp = await client.post("/api/ai/summarize", json={"email_text": "Test email body here"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_categorize_endpoint(self, client, mock_provider_override):
        resp = await client.post("/api/ai/categorize", json={"subject": "Hi", "body": "Test"})
        assert resp.status_code == 200
        assert resp.json()["result"] == "work"

    @pytest.mark.asyncio
    async def test_organize_endpoint(self, client, db_session, mock_provider_override):
        from app.models import EmailAccount, Email, ProviderType
        acct = EmailAccount(email="organize@test.com", provider=ProviderType.GMAIL)
        db_session.add(acct)
        await db_session.commit()

        db_session.add_all([
            Email(account_id=acct.id, provider_message_id="m1", from_address="a@b.com", to_addresses=acct.email,
                  subject="Invoice #123", body_text="Please pay invoice 123", folder="INBOX", received_at=datetime.datetime.now(datetime.UTC)),
            Email(account_id=acct.id, provider_message_id="m2", from_address="c@d.com", to_addresses=acct.email,
                  subject="Team lunch", body_text="Lunch tomorrow at noon", folder="INBOX", received_at=datetime.datetime.now(datetime.UTC)),
        ])
        await db_session.commit()

        resp = await client.post("/api/ai/organize", json={"folder": "INBOX", "limit": 50})
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data


class TestAIEndpointNoActiveProvider:
    @pytest.mark.asyncio
    async def test_draft_returns_400_when_no_active_provider(self, client):
        resp = await client.post("/api/ai/draft", json={"email_text": "Hello world"})
        assert resp.status_code == 400
        assert "No active AI provider" in resp.json()["detail"]


