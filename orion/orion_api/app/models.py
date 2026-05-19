from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="online")
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    commands: Mapped[list["CommandHistory"]] = relationship(back_populates="device")


class App(Base):
    __tablename__ = "apps"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    exec_path: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    aliases: Mapped[list["AppAlias"]] = relationship(
        back_populates="app", cascade="all, delete-orphan"
    )


class AppAlias(Base):
    __tablename__ = "app_aliases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("apps.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)

    app: Mapped["App"] = relationship(back_populates="aliases")


class CommandHistory(Base):
    __tablename__ = "command_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="success")
    response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)

    device: Mapped["Device | None"] = relationship(back_populates="commands")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pref_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    pref_value: Mapped[str] = mapped_column(Text, nullable=False)


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)