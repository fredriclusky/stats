from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    mappings: Mapped[list["CampaignMapping"]] = relationship("CampaignMapping", back_populates="campaign")


class CampaignMapping(Base):
    __tablename__ = "campaign_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("affiliate_accounts.id"), nullable=False)
    network_campaign_id: Mapped[str] = mapped_column(String(200), nullable=False)
    network_campaign_name: Mapped[str] = mapped_column(String(200), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="mappings")
    account: Mapped["AffiliateAccount"] = relationship("AffiliateAccount", back_populates="campaign_mappings")
    stats: Mapped[list] = relationship("AffiliateStat", back_populates="campaign_mapping")
    sub_ids: Mapped[list] = relationship("SubID", back_populates="campaign_mapping")
