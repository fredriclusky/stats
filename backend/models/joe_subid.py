from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base
import decimal


class JoeSubIdStat(Base):
    """
    One row per (account, date, joe_sub_id_value).
    Populated during sync by querying the network API grouped by Joe's tracking slot.
    HasOffers: affiliate_info2 (slot 2)  |  Everflow: sub1 (slot 1)
    """
    __tablename__ = "joe_sub_id_stats"
    __table_args__ = (
        UniqueConstraint("account_id", "stat_date", "sub_id_value", name="uq_joe_subid_account_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("affiliate_accounts.id"), nullable=False, index=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sub_id_value: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    revenue: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    offer_name: Mapped[str] = mapped_column(String(255), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["AffiliateAccount"] = relationship("AffiliateAccount")
