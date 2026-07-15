from app.ai.providers.base import AIProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.ollama import OllamaProvider


PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "custom": OpenAIProvider,  # OpenAI-compatible custom endpoints (Groq, DeepSeek, vLLM, etc.)
}


def get_provider(provider_type: str, **kwargs) -> AIProvider:
    cls = PROVIDER_REGISTRY.get(provider_type)
    if not cls:
        raise ValueError(f"Unknown provider: {provider_type}. Available: {list(PROVIDER_REGISTRY.keys())}")
    return cls(**kwargs)
