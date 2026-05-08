from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base
import decimal


class AffiliateConversion(Base):
    __tablename__ = "affiliate_conversions"
    __table_args__ = (
        UniqueConstraint("account_id", "network_conversion_id", name="uq_conversion_account_network_id"),
        Index("ix_affiliate_conversions_conversion_at", "conversion_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("affiliate_accounts.id"), nullable=False, index=True)
    network_conversion_id: Mapped[str] = mapped_column(String(200), nullable=False)
    conversion_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    campaign_id: Mapped[str] = mapped_column(String(100), nullable=True)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=True)
    sub_id: Mapped[str] = mapped_column(String(200), nullable=True)
    sub_id1: Mapped[str] = mapped_column(String(200), nullable=True)
    revenue: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["AffiliateAccount"] = relationship("AffiliateAccount")
