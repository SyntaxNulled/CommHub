from anthropic import AsyncAnthropic
from app.ai.providers.base import AIProvider, AIProviderConfig


class AnthropicProvider(AIProvider):
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model = config.model or "claude-sonnet-4-20250514"

    async def _call(self, system: str, user: str) -> str:
        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text if resp.content else ""

    async def draft_reply(self, email_text: str, tone: str = "professional") -> str:
        system = f"Write a {tone} email reply. Be concise and match the sender's tone. Output only the reply body."
        return await self._call(system, f"Original email:\n\n{email_text}")

    async def summarize_email(self, email_text: str) -> str:
        system = "Summarize the following email in 2-3 sentences. Extract key points, action items, and deadlines."
        return await self._call(system, email_text)

    async def categorize_email(self, subject: str, body: str) -> str:
        system = (
            "Categorize this email into exactly one: "
            "'work', 'personal', 'spam', 'newsletter', 'urgent', 'calendar', 'notification'. "
            "Reply with only the category word."
        )
        return await self._call(system, f"Subject: {subject}\n\n{body}")

    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        return await self._call(system_prompt or "You are a helpful AI assistant.", prompt)
