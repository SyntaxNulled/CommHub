from dataclasses import dataclass
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import AIProviderConfig as AIProviderConfigModel, Email
from app.ai.providers import get_provider, PROVIDER_REGISTRY
from app.ai.providers.base import AIProvider, AIProviderConfig

router = APIRouter(prefix="/api/ai", tags=["ai"])


# --- Schemas ---

class ProviderConfigCreate(BaseModel):
    provider_type: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    api_key: str = ""
    base_url: str | None = None
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024

class ProviderConfigUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=128)
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    is_active: bool | None = None
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1, le=32000)

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

class OrganizeRequest(BaseModel):
    folder: str = "INBOX"
    limit: int = Field(50, ge=1, le=200)

class OrganizeSuggestion(BaseModel):
    email_id: int
    subject: str
    suggested_folder: str
    reason: str

class OrganizeResponse(BaseModel):
    suggestions: list[OrganizeSuggestion]

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


async def _deactivate_others(db: AsyncSession, keep_id: int) -> None:
    """Enforce single-active-provider invariant."""
    await db.execute(
        update(AIProviderConfigModel)
        .where(AIProviderConfigModel.id != keep_id)
        .values(is_active=False)
    )


async def _is_duplicate_built_in(db: AsyncSession, provider_type: str, exclude_id: int | None = None) -> bool:
    """Built-in providers (openai, anthropic, ollama) can only have one config each."""
    if provider_type not in PROVIDER_REGISTRY or provider_type == "custom":
        return False
    q = select(AIProviderConfigModel).where(
        AIProviderConfigModel.provider_type == provider_type,
    )
    if exclude_id is not None:
        q = q.where(AIProviderConfigModel.id != exclude_id)
    result = await db.execute(q)
    return result.scalar_one_or_none() is not None


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

    if await _is_duplicate_built_in(db, cfg.provider_type):
        raise HTTPException(409, f"Provider '{cfg.provider_type}' already configured. Edit the existing config.")

    record = AIProviderConfigModel(**cfg.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _config_response(record)


@router.put("/configs/{config_id}")
async def update_config(config_id: int, cfg: ProviderConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.id == config_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, f"Provider config {config_id} not found.")

    updates = cfg.model_dump(exclude_unset=True)
    # Empty api_key on update means "keep existing" (the UI shows a masked value)
    if updates.get("api_key") == "":
        updates.pop("api_key")
    for field, value in updates.items():
        setattr(record, field, value)

    if updates.get("is_active"):
        await _deactivate_others(db, config_id)

    await db.commit()
    await db.refresh(record)
    return _config_response(record)


@router.delete("/configs/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AIProviderConfigModel).where(AIProviderConfigModel.id == config_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, f"Provider config {config_id} not found.")
    await db.delete(record)
    await db.commit()
    return {"deleted": config_id}


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


@router.post("/organize", response_model=OrganizeResponse)
async def organize_emails(
    req: OrganizeRequest,
    ap: ActiveProviderInfo = Depends(get_active_provider),
    db: AsyncSession = Depends(get_db),
):
    """Scan a folder of emails and return AI suggestions for folder organization."""
    from sqlalchemy import select, desc

    result = await db.execute(
        select(Email).where(Email.folder == req.folder).order_by(desc(Email.received_at)).limit(req.limit)
    )
    emails = result.scalars().all()
    if not emails:
        return OrganizeResponse(suggestions=[])

    prompt = _build_organize_prompt(emails, req.folder)
    ai_result = await _run_with_provider(
        ap,
        ap.provider.generate_response(
            prompt,
            system_prompt=(
                "You are an email assistant. Analyze the provided emails and suggest a folder "
                "for each one. Return ONLY a JSON array with objects: {email_id, subject, suggested_folder, reason}. "
                "Keep suggested_folder names short and user-friendly."
            )
        )
    )
    suggestions = _parse_organize_response(ai_result, emails)
    return OrganizeResponse(suggestions=suggestions)


def _build_organize_prompt(emails: list[Email], folder: str) -> str:
    lines = [f"Folder: {folder}", ""]
    for e in emails:
        lines.append(f"ID: {e.id}")
        lines.append(f"From: {e.from_address}")
        lines.append(f"Subject: {e.subject}")
        body_preview = (e.body_text or "")[:300].replace("\n", " ")
        lines.append(f"Body preview: {body_preview}")
        lines.append("")
    return "\n".join(lines)


def _parse_organize_response(result: str, emails: list[Email]) -> list[OrganizeSuggestion]:
    import json, re
    # Build a map for safe subject fallback
    email_map = {e.id: e for e in emails}
    # Try to extract JSON array from response (models sometimes wrap in markdown)
    text = result.strip()
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[-2] if text.count("```") >= 2 else text.split("```")[1]
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: attempt to fix trailing commas or single quotes
        text = re.sub(r",\s*([\]\}])", r"\1", text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    suggestions = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            email_id = int(item.get("email_id"))
            email = email_map.get(email_id)
            suggestions.append(OrganizeSuggestion(
                email_id=email_id,
                subject=str(item.get("subject", email.subject if email else "")),
                suggested_folder=str(item.get("suggested_folder", "INBOX")),
                reason=str(item.get("reason", "")),
            ))
        except (ValueError, TypeError):
            continue
    return suggestions
