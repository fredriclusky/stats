from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class SubID(Base):
    __tablename__ = "sub_ids"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=True)
    campaign_mapping_id: Mapped[int] = mapped_column(ForeignKey("campaign_mappings.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    campaign_mapping: Mapped["CampaignMapping"] = relationship("CampaignMapping", back_populates="sub_ids")
    mailing_events: Mapped[list] = relationship("MailingEvent", back_populates="sub_id_ref")
    outbound_logs: Mapped[list] = relationship("OutboundLog", back_populates="sub_id_ref")
