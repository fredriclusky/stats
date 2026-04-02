from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class AffiliateNetwork(Base):
    __tablename__ = "affiliate_networks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    network_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hasoffers, everflow, custom
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    accounts: Mapped[list["AffiliateAccount"]] = relationship("AffiliateAccount", back_populates="network")


class AffiliateAccount(Base):
    __tablename__ = "affiliate_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("affiliate_networks.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    api_base_url: Mapped[str] = mapped_column(String(255), nullable=True)
    network_id_value: Mapped[str] = mapped_column(String(100), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    network: Mapped["AffiliateNetwork"] = relationship("AffiliateNetwork", back_populates="accounts")
    campaign_mappings: Mapped[list] = relationship("CampaignMapping", back_populates="account")
