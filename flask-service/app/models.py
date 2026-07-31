from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "security_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("accounts_user.id"))
    scan_log_id: Mapped[int | None] = mapped_column(ForeignKey("security_scan_log.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    # Matches Django's FileField(upload_to="reports/") convention exactly:
    # this stores a path RELATIVE to MEDIA_ROOT, e.g. "reports/foo.pdf",
    # not an absolute filesystem path - so Django's report.file.url keeps
    # working without any change on that side once this service writes here.
    file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(lazy="joined")


class Notification(Base):
    __tablename__ = "notifications_notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("accounts_user.id"), nullable=True)
    recipient_id: Mapped[int | None] = mapped_column(ForeignKey("accounts_user.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
