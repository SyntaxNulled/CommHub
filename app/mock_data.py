import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
from app.models import EmailAccount, Email, CalendarEvent, ProviderType


FAKE_ACCOUNTS = [
    {"email": "nikot@work.com", "provider": ProviderType.GMAIL, "display_name": "Work"},
    {"email": "nikot@personal.com", "provider": ProviderType.OUTLOOK, "display_name": "Personal"},
]

FAKE_EMAILS = [
    {"folder": "INBOX", "from": "sarah@company.com", "from_name": "Sarah Chen", "subject": "Q3 Project Review", "body_text": "Hey Nikot,\n\nJust a reminder that the Q3 project review is scheduled for this Friday at 2pm. Please have the metrics ready.\n\nBest,\nSarah", "is_read": False, "received_at_days_ago": 0},
    {"folder": "INBOX", "from": "alerts@github.com", "from_name": "GitHub", "subject": "[commhub] Push to master (2 new commits)", "body_text": "nikot pushed 2 commits to master in commhub/commhub\n\n393c445 - Phase 7: Automation & Rules\n0ce04b4 - Phase 6: AI Engine", "is_read": True, "received_at_days_ago": 0},
    {"folder": "INBOX", "from": "mike@client.co", "from_name": "Mike Reynolds", "subject": "Invoice #1042 — Payment Confirmation", "body_text": "Hi,\n\nJust confirming we received your payment for invoice #1042. Thank you!\n\nRegards,\nMike", "is_read": True, "received_at_days_ago": 1},
    {"folder": "INBOX", "from": "newsletter@devweekly.com", "from_name": "Dev Weekly", "subject": "This Week in Tech: AI Agents, Rust 2.0, and more", "body_text": "Top stories this week:\n- AI agents are taking over\n- Rust 2.0 released\n- Python 4.0 proposals", "is_read": False, "received_at_days_ago": 1},
    {"folder": "INBOX", "from": "hr@company.com", "from_name": "HR Department", "subject": "Updated Holiday Calendar 2026", "body_text": "Please find attached the updated holiday calendar for the remainder of 2026.\n\nKey dates:\n- Aug 15: Company off-site\n- Sep 7: Labor Day\n- Nov 26-27: Thanksgiving", "is_read": False, "received_at_days_ago": 2},
    {"folder": "INBOX", "from": "alice@startup.io", "from_name": "Alice Wang", "subject": "Partnership opportunity — let's chat!", "body_text": "Hey Nikot,\n\nI came across your work on CommHub and I'm really impressed. I'd love to discuss a potential partnership opportunity.\n\nAre you free for a quick call next week?\n\nAlice", "is_read": True, "received_at_days_ago": 3},
    {"folder": "INBOX", "from": "noreply@amazon.com", "from_name": "Amazon", "subject": "Your order #303-124 has shipped", "body_text": "Your package is on its way!\n\nEstimated delivery: Thursday\n\nTrack your package at amazon.com/tracking", "is_read": True, "received_at_days_ago": 4},
    {"folder": "SENT", "from": "nikot@work.com", "from_name": "Nikot", "subject": "Re: Q3 Project Review", "body_text": "Hi Sarah,\n\nGot it. I'll have the metrics ready by Friday morning.\n\nBest,\nNikot", "is_read": True, "received_at_days_ago": 0},
    {"folder": "SENT", "from": "nikot@work.com", "from_name": "Nikot", "subject": "Updated deployment schedule", "body_text": "Team,\n\nI've updated the deployment schedule. Please review and let me know if there are any conflicts.\n\nhttps://docs.google.com/...\n\nNikot", "is_read": True, "received_at_days_ago": 1},
    {"folder": "SENT", "from": "nikot@personal.com", "from_name": "Nikot", "subject": "House sitting instructions", "body_text": "Hey,\n\nThanks for watching the place! Here's what you need to know:\n- Water the plants every other day\n- Mail is in the box by the door\n- Emergency number: 555-0123\n\nCheers,\nNikot", "is_read": True, "received_at_days_ago": 2},
    {"folder": "DRAFTS", "from": "nikot@work.com", "from_name": "Nikot", "subject": "Draft: Proposal for new project", "body_text": "Dear Team,\n\nI'm writing to propose a new initiative that I believe will significantly improve our workflow...\n\n[More details to come]", "is_read": True, "received_at_days_ago": 0},
    {"folder": "DRAFTS", "from": "nikot@personal.com", "from_name": "Nikot", "subject": "Draft: Birthday party invite", "body_text": "You're invited to my birthday party!\n\nDate: Saturday, August 8\nTime: 7pm\nLocation: My place\n\nLet me know if you can make it!", "is_read": True, "received_at_days_ago": 1},
    {"folder": "STARRED", "from": "boss@company.com", "from_name": "David Park", "subject": "Promotion discussion — Thursday 3pm", "body_text": "Nikot,\n\nI'd like to schedule a meeting to discuss your career progression and a potential promotion.\n\nThursday at 3pm works on my end.\n\n-David", "is_read": False, "received_at_days_ago": 0},
]

FAKE_EVENTS = [
    {"title": "Q3 Project Review", "description": "Quarterly review with Sarah", "start_days_from_now": 3, "start_hour": 14, "duration_hours": 1},
    {"title": "Promotion Discussion", "description": "Meeting with David about career progression", "start_days_from_now": 2, "start_hour": 15, "duration_hours": 1},
    {"title": "Team Standup", "description": "Daily standup with engineering team", "start_days_from_now": 0, "start_hour": 9, "duration_hours": 0.5},
    {"title": "Lunch with Alice", "description": "Partnership discussion with Alice Wang", "start_days_from_now": 4, "start_hour": 12, "duration_hours": 1},
    {"title": "Dentist Appointment", "description": "Regular checkup", "start_days_from_now": 5, "start_hour": 10, "duration_hours": 1},
    {"title": "Company Off-site", "description": "Annual company off-site event", "start_days_from_now": 7, "start_hour": 8, "duration_hours": 8},
    {"title": "Gym", "description": "Weekly gym session", "start_days_from_now": 1, "start_hour": 7, "duration_hours": 1},
    {"title": "Code Review Session", "description": "Review PRs with the team", "start_days_from_now": 2, "start_hour": 11, "duration_hours": 1.5},
]


async def seed_demo_data():
    async with async_session_factory() as session:
        existing = await session.execute(select(EmailAccount))
        if existing.scalars().first():
            return {"status": "already_seeded"}

        now = datetime.datetime.utcnow()

        for acct_data in FAKE_ACCOUNTS:
            acct = EmailAccount(
                email=acct_data["email"],
                provider=acct_data["provider"],
                display_name=acct_data["display_name"],
            )
            session.add(acct)
            await session.flush()

            for email_data in FAKE_EMAILS:
                received = now - datetime.timedelta(days=email_data["received_at_days_ago"])
                email = Email(
                    account_id=acct.id,
                    provider_message_id=f"mock-{acct.id}-{hash(email_data['subject'])}",
                    thread_id=None,
                    from_address=email_data["from"],
                    from_name=email_data["from_name"],
                    to_addresses=acct.email,
                    subject=email_data["subject"],
                    body_text=email_data["body_text"],
                    is_read=email_data["is_read"],
                    is_starred=(email_data["folder"] == "STARRED"),
                    folder=email_data["folder"],
                    received_at=received,
                )
                session.add(email)

        for evt_data in FAKE_EVENTS:
            start = now + datetime.timedelta(days=evt_data["start_days_from_now"])
            start = start.replace(hour=evt_data["start_hour"], minute=0, second=0, microsecond=0)
            end = start + datetime.timedelta(hours=evt_data["duration_hours"])
            event = CalendarEvent(
                account_id=1,
                provider_event_id=f"mock-ev-{hash(evt_data['title'])}",
                title=evt_data["title"],
                description=evt_data["description"],
                start_time=start,
                end_time=end,
            )
            session.add(event)

        await session.commit()
        return {"status": "seeded", "accounts": len(FAKE_ACCOUNTS), "emails": len(FAKE_EMAILS) * len(FAKE_ACCOUNTS), "events": len(FAKE_EVENTS)}
