from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base
import decimal


class AffiliateStat(Base):
    __tablename__ = "affiliate_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_mapping_id: Mapped[int] = mapped_column(ForeignKey("campaign_mappings.id"), nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), default=0)
    payout: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), default=0)
    sub_id: Mapped[str] = mapped_column(String(200), nullable=True)   # affiliate_info2 — Joe's Sub ID
    sub_id1: Mapped[str] = mapped_column(String(200), nullable=True)  # affiliate_info1 — campaign identifier
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign_mapping: Mapped["CampaignMapping"] = relationship("CampaignMapping", back_populates="stats")
