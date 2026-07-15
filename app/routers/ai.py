from dataclasses import dataclass
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import AIProviderConfig as AIProviderConfigModel
from app.ai.providers import get_provider, PROVIDER_REGISTRY
from app.ai.providers.base import AIProvider, AIProviderConfig

router = APIRouter(prefix="/api/ai", tags=["ai"])


# --- Schemas ---

class ProviderConfigCreate(BaseModel):
    provider_type: str
    display_name: str
    api_key: str = ""
    base_url: str | None = None
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024

class ProviderConfigUpdate(BaseModel):
    display_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    is_active: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None

class ProviderConfigResponse(BaseModel):
    id: int
    provider_type: str
    display_name: str
    api_key: str
    base_url: str | None
    model: str
    is_active: bool
    temperature: float
    max_tokens: int

class DraftRequest(BaseModel):
    email_text: str
    tone: str = "professional"

class SummarizeRequest(BaseModel):
    email_text: str

class CategorizeRequest(BaseModel):
    subject: str
    body: str

class ChatRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None

@dataclass
class ActiveProviderInfo:
    provider: AIProvider
    provider_type: str
    model: str

class AIResponse(BaseModel):
    result: str
    provider: str
    model: str


# --- Dependencies ---

async def get_active_provider(db: AsyncSession = Depends(get_db)) -> ActiveProviderInfo:
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.is_active == True)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(400, "No active AI provider configured. Set one up in Settings.")
    cfg = AIProviderConfig(
        api_key=record.api_key, base_url=record.base_url, model=record.model,
        temperature=record.temperature, max_tokens=record.max_tokens,
    )
    provider = get_provider(record.provider_type, config=cfg)
    return ActiveProviderInfo(provider=provider, provider_type=record.provider_type, model=record.model)


# --- Endpoints ---

@router.get("/providers")
async def list_available_providers():
    return list(PROVIDER_REGISTRY.keys())


@router.get("/configs")
async def list_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProviderConfigModel))
    configs = result.scalars().all()
    return [
        ProviderConfigResponse(
            id=c.id, provider_type=c.provider_type, display_name=c.display_name,
            api_key=c.api_key, base_url=c.base_url, model=c.model,
            is_active=c.is_active, temperature=c.temperature, max_tokens=c.max_tokens,
        )
        for c in configs
    ]


@router.post("/configs")
async def create_config(cfg: ProviderConfigCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.provider_type == cfg.provider_type)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Provider '{cfg.provider_type}' already configured. Use PUT to update.")

    record = AIProviderConfigModel(**cfg.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return ProviderConfigResponse(
        id=record.id, provider_type=record.provider_type, display_name=record.display_name,
        api_key=record.api_key, base_url=record.base_url, model=record.model,
        is_active=record.is_active, temperature=record.temperature, max_tokens=record.max_tokens,
    )


@router.put("/configs/{provider_type}")
async def update_config(provider_type: str, cfg: ProviderConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.provider_type == provider_type)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, f"Provider '{provider_type}' not found. Use POST to create.")

    for field, value in cfg.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return ProviderConfigResponse(
        id=record.id, provider_type=record.provider_type, display_name=record.display_name,
        api_key=record.api_key, base_url=record.base_url, model=record.model,
        is_active=record.is_active, temperature=record.temperature, max_tokens=record.max_tokens,
    )


@router.delete("/configs/{provider_type}")
async def delete_config(provider_type: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.provider_type == provider_type)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, f"Provider '{provider_type}' not found.")
    await db.delete(record)
    await db.commit()
    return {"deleted": provider_type}


@router.post("/draft", response_model=AIResponse)
async def draft_reply(req: DraftRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await ap.provider.draft_reply(req.email_text, tone=req.tone)
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)


@router.post("/summarize", response_model=AIResponse)
async def summarize_email(req: SummarizeRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await ap.provider.summarize_email(req.email_text)
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)


@router.post("/categorize", response_model=AIResponse)
async def categorize_email(req: CategorizeRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await ap.provider.categorize_email(req.subject, req.body)
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)


@router.post("/chat", response_model=AIResponse)
async def chat(req: ChatRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await ap.provider.generate_response(req.prompt, system_prompt=req.system_prompt)
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)
