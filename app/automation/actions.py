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


ACTION_HANDLERS = {
    "auto_reply": handle_auto_reply,
    "categorize": handle_categorize,
    "mark_read": handle_mark_read,
    "star": handle_star,
    "forward": handle_forward,
}


def execute_action(rule_name: str, action_type: str, action_config: dict, context: dict | None = None) -> dict:
    handler = ACTION_HANDLERS.get(action_type)
    if not handler:
        logger.warning(f"[{rule_name}] Unknown action type: {action_type}")
        return {"action": "unknown", "error": f"No handler for {action_type}"}
    return handler(rule_name, action_config, context)
