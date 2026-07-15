import asyncio
import logging

logger = logging.getLogger(__name__)


def handle_auto_reply(rule_name: str, action_config: dict, context: dict | None = None):
    subject = action_config.get("subject", f"Re: {context.get('subject', '')}" if context else "Auto-reply")
    body = action_config.get("body", "Thank you for your message. I will get back to you soon.")
    logger.info(f"[{rule_name}] Auto-reply: '{subject}' — {body[:60]}...")
    return {"action": "auto_reply", "subject": subject, "body": body}


def handle_categorize(rule_name: str, action_config: dict, context: dict | None = None):
    category = action_config.get("category", "general")
    logger.info(f"[{rule_name}] Categorize as: {category}")
    return {"action": "categorize", "category": category}


def handle_mark_read(rule_name: str, action_config: dict, context: dict | None = None):
    logger.info(f"[{rule_name}] Mark as read")
    return {"action": "mark_read"}


def handle_star(rule_name: str, action_config: dict, context: dict | None = None):
    logger.info(f"[{rule_name}] Starred")
    return {"action": "star"}


def handle_forward(rule_name: str, action_config: dict, context: dict | None = None):
    to = action_config.get("to", "")
    logger.info(f"[{rule_name}] Forward to: {to}")
    return {"action": "forward", "to": to}


async def handle_ai_categorize(rule_name: str, action_config: dict, context: dict | None = None) -> dict:
    """Use the active AI provider to pick a folder for an email, then move it."""
    if not context or "email_id" not in context:
        return {"action": "ai_categorize", "error": "No email_id in context"}

    from app.database import async_session_factory
    from app.models import Email, Folder
    from app.routers.ai import get_active_provider
    from sqlalchemy import select, update

    email_id = context["email_id"]
    async with async_session_factory() as session:
        result = await session.execute(select(Email).where(Email.id == email_id))
        email = result.scalar_one_or_none()
        if not email:
            return {"action": "ai_categorize", "error": "Email not found"}

        try:
            provider_info = await get_active_provider(session)
        except Exception as exc:
            logger.warning(f"[{rule_name}] No active AI provider for ai_categorize: {exc}")
            return {"action": "ai_categorize", "error": "No active AI provider"}

        try:
            prompt = f"Subject: {email.subject}\n\n{email.body_text or ''}"[:2000]
            suggested = await provider_info.provider.categorize_email(email.subject, email.body_text or "")
            suggested_folder = suggested.strip().upper().replace(" ", "_")
            # Validate against known folders; default to INBOX if unknown
            folder_result = await session.execute(
                select(Folder).where(Folder.normalized_name == suggested_folder)
            )
            if folder_result.scalar_one_or_none() is None:
                suggested_folder = action_config.get("fallback_folder", "INBOX")
            await session.execute(
                update(Email)
                .where(Email.id == email_id)
                .values(folder=suggested_folder, is_read=False if suggested_folder == "INBOX" else email.is_read)
            )
            await session.commit()
            logger.info(f"[{rule_name}] AI categorized email {email_id} into {suggested_folder}")
            return {"action": "ai_categorize", "folder": suggested_folder}
        except Exception as exc:
            logger.warning(f"[{rule_name}] AI categorization failed: {exc}")
            return {"action": "ai_categorize", "error": str(exc)}
        finally:
            close = getattr(provider_info.provider, "close", None)
            if close:
                try:
                    await close()
                except Exception:
                    pass


ACTION_HANDLERS = {
    "auto_reply": handle_auto_reply,
    "categorize": handle_categorize,
    "mark_read": handle_mark_read,
    "star": handle_star,
    "forward": handle_forward,
    "ai_categorize": handle_ai_categorize,
}


async def execute_action(rule_name: str, action_type: str, action_config: dict, context: dict | None = None) -> dict:
    handler = ACTION_HANDLERS.get(action_type)
    if not handler:
        logger.warning(f"[{rule_name}] Unknown action type: {action_type}")
        return {"action": "unknown", "error": f"No handler for {action_type}"}
    if asyncio.iscoroutinefunction(handler):
        return await handler(rule_name, action_config, context)
    return handler(rule_name, action_config, context)
