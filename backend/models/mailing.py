from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base
import decimal


class MailingEvent(Base):
    __tablename__ = "mailing_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    sub_id_id: Mapped[int] = mapped_column(ForeignKey("sub_ids.id"), nullable=True)
    sub_id_value: Mapped[str] = mapped_column(String(200), nullable=True)
    prompt_used: Mapped[str] = mapped_column(Text, nullable=True)
    list_used: Mapped[str] = mapped_column(String(500), nullable=True)
    sends: Mapped[int] = mapped_column(Integer, nullable=True)
    opens: Mapped[int] = mapped_column(Integer, nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sub_id_ref: Mapped["SubID"] = relationship("SubID", back_populates="mailing_events")


class OutboundLog(Base):
    __tablename__ = "outbound_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    sub_id_id: Mapped[int] = mapped_column(ForeignKey("sub_ids.id"), nullable=True)
    sub_id_value: Mapped[str] = mapped_column(String(200), nullable=True)
    revenue_sent: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    request_data: Mapped[dict] = mapped_column(JSON, default=dict)
    response_status: Mapped[int] = mapped_column(Integer, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sub_id_ref: Mapped["SubID"] = relationship("SubID", back_populates="outbound_logs")
