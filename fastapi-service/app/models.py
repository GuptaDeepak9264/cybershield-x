from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """
    Read-mostly mirror of Django's accounts_user table.

    Only the columns this service actually needs are declared -
    SQLAlchemy doesn't require mapping every column in the table, and
    deliberately NOT mapping `password` here means this service can never
    accidentally read/write a password hash even by mistake.

    Django owns this table's schema (via its migrations). If a Django
    migration ever renames/drops one of the columns below, this mapping
    breaks loudly at startup - which is the correct failure mode for a
    cross-service schema mismatch, not a silent one.
    """

    __tablename__ = "accounts_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(default=True)


class ScanLog(Base):
    __tablename__ = "security_scan_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("accounts_user.id"))
    scan_type: Mapped[str] = mapped_column(String(10))
    target: Mapped[str] = mapped_column(String(500))
    file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="PENDING")
    security_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(lazy="joined")


class ThreatIntelEntry(Base):
    __tablename__ = "security_threat_intel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    indicator: Mapped[str] = mapped_column(String(500), unique=True)
    indicator_type: Mapped[str] = mapped_column(String(10))
    severity: Mapped[str] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(Text, default="")
    added_by_id: Mapped[int | None] = mapped_column(ForeignKey("accounts_user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
