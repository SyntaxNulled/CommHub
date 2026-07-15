import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    emails: Mapped[list["Email"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    calendar_events: Mapped[list["CalendarEvent"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_accounts.id"))
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
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    folder: Mapped[str] = mapped_column(String(128), default="INBOX")
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    account: Mapped["EmailAccount"] = relationship(back_populates="emails")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_accounts.id"))
    provider_event_id: Mapped[str] = mapped_column(String(512), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    account: Mapped["EmailAccount"] = relationship(back_populates="calendar_events")


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("email_accounts.id"), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(64))
    trigger_config: Mapped[dict] = mapped_column(JSON, default=dict)
    action_type: Mapped[str] = mapped_column(String(64))
    action_config: Mapped[dict] = mapped_column(JSON, default=dict)
    cron_schedule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
