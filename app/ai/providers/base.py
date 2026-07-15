from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AIProviderConfig:
    api_key: str = ""
    base_url: str | None = None
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    extra_params: dict[str, Any] | None = None


class AIProvider(ABC):
    def __init__(self, config: AIProviderConfig):
        self.config = config

    @abstractmethod
    async def draft_reply(self, email_text: str, tone: str = "professional") -> str:
        ...

    @abstractmethod
    async def summarize_email(self, email_text: str) -> str:
        ...

    @abstractmethod
    async def categorize_email(self, subject: str, body: str) -> str:
        ...

    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str | None = None) -> str:
        ...
