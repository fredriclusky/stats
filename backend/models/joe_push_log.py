from datetime import datetime, date
from sqlalchemy import DateTime, Date, Numeric, String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
import decimal


class JoePushLog(Base):
    """
    One row per sub_id_value.
    Tracks what revenue was last successfully pushed to Joe and on which date,
    so we can push every new day and skip intra-day dupes where nothing changed.
    """
    __tablename__ = "joe_push_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    sub_id_value: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    last_sent_revenue: Mapped[decimal.Decimal] = mapped_column(Numeric(12, 2), default=0)
    last_sent_date: Mapped[date] = mapped_column(Date, nullable=True)
    push_count: Mapped[int] = mapped_column(Integer, default=0)
    last_pushed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(String(500), nullable=True)
