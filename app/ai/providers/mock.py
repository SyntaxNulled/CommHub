from app.ai.providers.base import AIProvider, AIProviderConfig


class MockProvider(AIProvider):
    def __init__(self, config: AIProviderConfig | None = None):
        super().__init__(config or AIProviderConfig())

    async def draft_reply(self, email_text: str, tone: str = "professional") -> str:
        return f"[Mock {tone} draft reply to: {email_text[:50]}...]"

    async def summarize_email(self, email_text: str) -> str:
        return f"[Mock summary of {len(email_text)} chars]"

    async def categorize_email(self, subject: str, body: str) -> str:
        return "work"

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"[Mock response to: {prompt[:50]}...]"
