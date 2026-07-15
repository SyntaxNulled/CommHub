import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, Index, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


def utcnow() -> datetime.datetime:
    """Naive UTC timestamp — consistent with client-supplied naive datetimes in SQLite."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class ProviderType(str, enum.Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    provider: Mapped[ProviderType] = mapped_column(SAEnum(ProviderType))
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    oauth_token_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    emails: Mapped[list["Email"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_accounts.id"), index=True)
    provider_message_id: Mapped[str] = mapped_column(String(512), index=True)
    thread_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    from_address: Mapped[str] = mapped_column(String(320))
    from_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    to_addresses: Mapped[str] = mapped_column(Text)
    cc_addresses: Mapped[str | None] = mapped_column(Text, nullable=True)
    bcc_addresses: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str] = mapped_column(String(998))
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    folder: Mapped[str] = mapped_column(String(128), default="INBOX")
    snoozed_until: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    send_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

    account: Mapped["EmailAccount"] = relationship(back_populates="emails")

    __table_args__ = (
        Index("ix_emails_folder_received", "folder", "received_at"),
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_accounts.id"), index=True)
    provider_event_id: Mapped[str] = mapped_column(String(512), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)

    account: Mapped["EmailAccount"] = relationship(back_populates="calendar_events")


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    normalized_name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("email_accounts.id"), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(64))
    trigger_config: Mapped[dict] = mapped_column(JSON, default=dict)
    action_type: Mapped[str] = mapped_column(String(64))
    action_config: Mapped[dict] = mapped_column(JSON, default=dict)
    cron_schedule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)


class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    api_key: Mapped[str] = mapped_column(Text, default="")
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    model: Mapped[str] = mapped_column(String(128), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(default=1024)
    extra_params: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
