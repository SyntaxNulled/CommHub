import httpx
from app.ai.providers.base import AIProvider, AIProviderConfig


OLLAMA_DEFAULT_URL = "http://localhost:11434"


class OllamaProvider(AIProvider):
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or OLLAMA_DEFAULT_URL
        self.model = config.model or "llama3"
        self.http = httpx.AsyncClient(base_url=self.base_url, timeout=60)

    async def _call(self, system: str, user: str) -> str:
        resp = await self.http.post("/api/chat", json={
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        })
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

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

    async def close(self):
        await self.http.aclose()
