from dataclasses import dataclass
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
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
    api_key_masked: str
    has_api_key: bool
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


def _mask_key(key: str | None) -> str:
    """Mask an API key for safe display: 'sk-...abcd' or ''."""
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:3]}...{key[-4:]}"


def _config_response(c: AIProviderConfigModel) -> ProviderConfigResponse:
    return ProviderConfigResponse(
        id=c.id, provider_type=c.provider_type, display_name=c.display_name,
        api_key_masked=_mask_key(c.api_key), has_api_key=bool(c.api_key),
        base_url=c.base_url, model=c.model,
        is_active=c.is_active, temperature=c.temperature, max_tokens=c.max_tokens,
    )


async def _deactivate_others(db: AsyncSession, keep_provider_type: str) -> None:
    """Enforce single-active-provider invariant."""
    await db.execute(
        update(AIProviderConfigModel)
        .where(AIProviderConfigModel.provider_type != keep_provider_type)
        .values(is_active=False)
    )


# --- Dependencies ---

async def get_active_provider(db: AsyncSession = Depends(get_db)) -> ActiveProviderInfo:
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.is_active == True)
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(400, "No active AI provider configured. Set one up in Settings.")
    cfg = AIProviderConfig(
        api_key=record.api_key, base_url=record.base_url, model=record.model,
        temperature=record.temperature, max_tokens=record.max_tokens,
    )
    try:
        provider = get_provider(record.provider_type, config=cfg)
    except ValueError:
        raise HTTPException(400, f"Active provider '{record.provider_type}' is not supported. Reconfigure in Settings.")
    return ActiveProviderInfo(provider=provider, provider_type=record.provider_type, model=record.model)


async def _run_with_provider(ap: ActiveProviderInfo, coro):
    """Await an AI call and always release provider resources afterwards."""
    try:
        return await coro
    finally:
        close = getattr(ap.provider, "close", None)
        if close:
            try:
                await close()
            except Exception:
                pass


# --- Endpoints ---

@router.get("/providers")
async def list_available_providers():
    return list(PROVIDER_REGISTRY.keys())


@router.get("/configs")
async def list_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProviderConfigModel))
    return [_config_response(c) for c in result.scalars().all()]


@router.post("/configs", status_code=201)
async def create_config(cfg: ProviderConfigCreate, db: AsyncSession = Depends(get_db)):
    if cfg.provider_type not in PROVIDER_REGISTRY:
        raise HTTPException(400, f"Unknown provider type '{cfg.provider_type}'. Available: {list(PROVIDER_REGISTRY.keys())}")

    existing = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.provider_type == cfg.provider_type)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Provider '{cfg.provider_type}' already configured. Use PUT to update.")

    record = AIProviderConfigModel(**cfg.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _config_response(record)


@router.put("/configs/{provider_type}")
async def update_config(provider_type: str, cfg: ProviderConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.provider_type == provider_type)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, f"Provider '{provider_type}' not found. Use POST to create.")

    updates = cfg.model_dump(exclude_unset=True)
    # Empty api_key on update means "keep existing" (the UI shows a masked value)
    if updates.get("api_key") == "":
        updates.pop("api_key")
    for field, value in updates.items():
        setattr(record, field, value)

    if updates.get("is_active"):
        await _deactivate_others(db, provider_type)

    await db.commit()
    await db.refresh(record)
    return _config_response(record)


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
    result = await _run_with_provider(ap, ap.provider.draft_reply(req.email_text, tone=req.tone))
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)


@router.post("/summarize", response_model=AIResponse)
async def summarize_email(req: SummarizeRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await _run_with_provider(ap, ap.provider.summarize_email(req.email_text))
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)


@router.post("/categorize", response_model=AIResponse)
async def categorize_email(req: CategorizeRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await _run_with_provider(ap, ap.provider.categorize_email(req.subject, req.body))
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)


@router.post("/chat", response_model=AIResponse)
async def chat(req: ChatRequest, ap: ActiveProviderInfo = Depends(get_active_provider)):
    result = await _run_with_provider(ap, ap.provider.generate_response(req.prompt, system_prompt=req.system_prompt))
    return AIResponse(result=result, provider=ap.provider_type, model=ap.model)
