from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import AutomationRule
from app.automation.scheduler import add_cron_job, remove_job, get_scheduled_jobs

router = APIRouter(prefix="/api/automation", tags=["automation"])

TRIGGER_TYPES = ["new_email", "keyword_match", "cron_schedule"]
ACTION_TYPES = ["auto_reply", "categorize", "mark_read", "star", "forward"]


class RuleCreate(BaseModel):
    name: str
    description: str = ""
    account_id: int | None = None
    trigger_type: str
    trigger_config: dict = {}
    action_type: str
    action_config: dict = {}
    cron_schedule: str | None = None
    is_enabled: bool = True


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    account_id: int | None = None
    trigger_type: str | None = None
    trigger_config: dict | None = None
    action_type: str | None = None
    action_config: dict | None = None
    cron_schedule: str | None = None
    is_enabled: bool | None = None


class RuleResponse(BaseModel):
    id: int
    name: str
    description: str
    account_id: int | None
    is_enabled: bool
    trigger_type: str
    trigger_config: dict
    action_type: str
    action_config: dict
    cron_schedule: str | None


@router.get("/trigger-types")
async def list_trigger_types():
    return TRIGGER_TYPES


@router.get("/action-types")
async def list_action_types():
    return ACTION_TYPES


@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).order_by(AutomationRule.created_at.desc()))
    rules = result.scalars().all()
    return [
        RuleResponse(
            id=r.id, name=r.name, description=r.description or "",
            account_id=r.account_id, is_enabled=r.is_enabled,
            trigger_type=r.trigger_type, trigger_config=r.trigger_config or {},
            action_type=r.action_type, action_config=r.action_config or {},
            cron_schedule=r.cron_schedule,
        )
        for r in rules
    ]


@router.post("/rules", response_model=RuleResponse)
async def create_rule(rule: RuleCreate, db: AsyncSession = Depends(get_db)):
    if rule.trigger_type not in TRIGGER_TYPES:
        raise HTTPException(400, f"Invalid trigger type. Must be one of: {TRIGGER_TYPES}")
    if rule.action_type not in ACTION_TYPES:
        raise HTTPException(400, f"Invalid action type. Must be one of: {ACTION_TYPES}")
    if rule.trigger_type == "cron_schedule" and not rule.cron_schedule:
        raise HTTPException(400, "cron_schedule is required for cron_schedule trigger type")

    record = AutomationRule(
        name=rule.name, description=rule.description, account_id=rule.account_id,
        is_enabled=rule.is_enabled, trigger_type=rule.trigger_type,
        trigger_config=rule.trigger_config, action_type=rule.action_type,
        action_config=rule.action_config, cron_schedule=rule.cron_schedule,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    if record.is_enabled and record.trigger_type == "cron_schedule" and record.cron_schedule:
        from app.automation.engine import execute_cron_rule
        add_cron_job(execute_cron_rule, record.id, record.cron_schedule)

    return _rule_to_response(record)


@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, update: RuleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Rule not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)

    remove_job(rule_id)
    if record.is_enabled and record.trigger_type == "cron_schedule" and record.cron_schedule:
        from app.automation.engine import execute_cron_rule
        add_cron_job(execute_cron_rule, record.id, record.cron_schedule)

    return _rule_to_response(record)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Rule not found")
    await db.delete(record)
    await db.commit()
    remove_job(rule_id)
    return {"deleted": rule_id}


@router.get("/scheduler/jobs")
async def list_scheduled_jobs():
    return get_scheduled_jobs()


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AutomationRule).where(AutomationRule.id == rule_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Rule not found")
    record.is_enabled = not record.is_enabled
    await db.commit()
    await db.refresh(record)

    if record.is_enabled and record.trigger_type == "cron_schedule" and record.cron_schedule:
        from app.automation.engine import execute_cron_rule
        add_cron_job(execute_cron_rule, record.id, record.cron_schedule)
    else:
        remove_job(rule_id)

    return _rule_to_response(record)


@router.post("/test-trigger")
async def test_trigger(trigger_type: str, db: AsyncSession = Depends(get_db)):
    from app.automation.engine import evaluate_trigger
    context = {"subject": "Test", "from": "test@example.com", "body": "This is a test"}
    results = await evaluate_trigger(db, trigger_type, context)
    return {"matched_rules": len(results), "results": results}


def _rule_to_response(r: AutomationRule) -> RuleResponse:
    return RuleResponse(
        id=r.id, name=r.name, description=r.description or "",
        account_id=r.account_id, is_enabled=r.is_enabled,
        trigger_type=r.trigger_type, trigger_config=r.trigger_config or {},
        action_type=r.action_type, action_config=r.action_config or {},
        cron_schedule=r.cron_schedule,
    )
