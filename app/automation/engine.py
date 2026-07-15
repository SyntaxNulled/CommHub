import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AutomationRule
from app.automation.actions import execute_action

logger = logging.getLogger(__name__)


async def evaluate_trigger(session: AsyncSession, trigger_type: str, context: dict):
    result = await session.execute(
        select(AutomationRule).where(
            AutomationRule.is_enabled == True,
            AutomationRule.trigger_type == trigger_type,
        )
    )
    rules = result.scalars().all()

    outputs = []
    for rule in rules:
        if _matches_trigger(rule.trigger_config, context):
            logger.info(f"Rule '{rule.name}' triggered ({trigger_type})")
            output = execute_action(rule.name, rule.action_type, rule.action_config, context)
            outputs.append({"rule_id": rule.id, "rule_name": rule.name, "output": output})
    return outputs


def _matches_trigger(trigger_config: dict, context: dict) -> bool:
    for key, expected in trigger_config.items():
        actual = context.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif isinstance(expected, str) and expected.startswith("re:"):
            import re
            if not re.search(expected[3:], str(actual or ""), re.IGNORECASE):
                return False
        else:
            if actual != expected:
                return False
    return True


async def execute_cron_rule(rule_id: int):
    from app.database import async_session_factory
    async with async_session_factory() as session:
        result = await session.execute(
            select(AutomationRule).where(AutomationRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()
        if not rule or not rule.is_enabled:
            return
        logger.info(f"Cron job executing rule '{rule.name}' (id={rule_id})")
        execute_action(rule.name, rule.action_type, rule.action_config)
