from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
import datetime
import zoneinfo

EASTERN = zoneinfo.ZoneInfo("America/New_York")

def today_eastern() -> datetime.date:
    return datetime.datetime.now(EASTERN).date()
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.database import get_db
from backend.models.stats import AffiliateStat
from backend.models.campaign import Campaign, CampaignMapping
from backend.models.affiliate import AffiliateAccount, AffiliateNetwork
from backend.routers.auth import require_admin, require_any_role

router = APIRouter(prefix="/api/stats", tags=["stats"])


def get_date_range(period: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Return (start, end) dates. Custom start_date/end_date override period."""
    if start_date and end_date:
        try:
            return datetime.date.fromisoformat(start_date), datetime.date.fromisoformat(end_date)
        except ValueError:
            pass
    today = today_eastern()
    if period == "today":
        return today, today
    elif period == "yesterday":
        return today - timedelta(days=1), today - timedelta(days=1)
    elif period == "week":
        return today - timedelta(days=6), today
    elif period == "month":
        return today - timedelta(days=29), today
    elif period == "year":
        return today - timedelta(days=364), today
    else:
        return today - timedelta(days=29), today


@router.get("/summary")
async def get_summary(
    period: str = Query("today", enum=["today", "yesterday", "week", "month", "year", "all", "custom"]),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    account_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role)
):
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
    )

    filters = [AffiliateStat.stat_date >= start, AffiliateStat.stat_date <= end]
    if account_id:
        filters.append(CampaignMapping.account_id == account_id)
    if campaign_id:
        filters.append(CampaignMapping.campaign_id == campaign_id)

    q = q.where(and_(*filters))
    result = await db.execute(q)
    row = result.one()
    return {
        "period": period,
        "start": str(start),
        "end": str(end),
        "revenue": float(row.revenue),
        "clicks": int(row.clicks),
        "conversions": int(row.conversions),
    }


@router.get("/by-campaign")
async def stats_by_campaign(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    account_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role)
):
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            Campaign.id.label("campaign_id"),
            Campaign.name.label("campaign_name"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(Campaign, CampaignMapping.campaign_id == Campaign.id)
        .where(AffiliateStat.stat_date >= start, AffiliateStat.stat_date <= end)
        .group_by(Campaign.id, Campaign.name)
        .order_by(func.sum(AffiliateStat.revenue).desc())
    )
    if account_id:
        q = q.where(CampaignMapping.account_id == account_id)

    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "campaign_id": r.campaign_id, "campaign_name": r.campaign_name,
            "revenue": float(r.revenue), "clicks": int(r.clicks), "conversions": int(r.conversions)
        }
        for r in rows
    ]


@router.get("/by-account")
async def stats_by_account(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            AffiliateAccount.id.label("account_id"),
            AffiliateAccount.label.label("account_label"),
            AffiliateNetwork.name.label("network_name"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(AffiliateNetwork, AffiliateAccount.network_id == AffiliateNetwork.id)
        .outerjoin(CampaignMapping, CampaignMapping.account_id == AffiliateAccount.id)
        .outerjoin(
            AffiliateStat,
            and_(
                AffiliateStat.campaign_mapping_id == CampaignMapping.id,
                AffiliateStat.stat_date >= start,
                AffiliateStat.stat_date <= end,
            )
        )
        .where(AffiliateAccount.active == True, AffiliateNetwork.active == True)
        .group_by(AffiliateAccount.id, AffiliateAccount.label, AffiliateNetwork.name)
        .order_by(func.coalesce(func.sum(AffiliateStat.revenue), 0).desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "account_id": r.account_id, "account_label": r.account_label,
            "network_name": r.network_name,
            "revenue": float(r.revenue), "clicks": int(r.clicks), "conversions": int(r.conversions)
        }
        for r in rows
    ]


@router.get("/daily")
async def stats_daily(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    campaign_id: Optional[int] = None,
    account_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role)
):
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            AffiliateStat.stat_date.label("stat_date"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .where(AffiliateStat.stat_date >= start, AffiliateStat.stat_date <= end)
        .group_by(AffiliateStat.stat_date)
        .order_by(AffiliateStat.stat_date)
    )
    if campaign_id:
        q = q.where(CampaignMapping.campaign_id == campaign_id)
    if account_id:
        q = q.where(CampaignMapping.account_id == account_id)

    result = await db.execute(q)
    rows = result.all()
    return [
        {"date": str(r.stat_date), "revenue": float(r.revenue), "clicks": int(r.clicks), "conversions": int(r.conversions)}
        for r in rows
    ]


@router.get("/by-subid")
async def stats_by_subid(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            AffiliateStat.sub_id.label("sub_id"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .where(
            AffiliateStat.stat_date >= start,
            AffiliateStat.stat_date <= end,
            AffiliateStat.sub_id.isnot(None)
        )
        .group_by(AffiliateStat.sub_id)
        .order_by(func.sum(AffiliateStat.revenue).desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {"sub_id": r.sub_id, "revenue": float(r.revenue), "clicks": int(r.clicks), "conversions": int(r.conversions)}
        for r in rows
    ]


@router.get("/by-sub1")
async def stats_by_sub1(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    """Stats grouped by sub_id1 (affiliate_info1 — campaign identifier shared across accounts)."""
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            AffiliateStat.sub_id1.label("sub_id1"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .where(
            AffiliateStat.stat_date >= start,
            AffiliateStat.stat_date <= end,
            AffiliateStat.sub_id1.isnot(None)
        )
        .group_by(AffiliateStat.sub_id1)
        .order_by(func.sum(AffiliateStat.revenue).desc())
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {"sub_id1": r.sub_id1, "revenue": float(r.revenue), "clicks": int(r.clicks), "conversions": int(r.conversions)}
        for r in rows
    ]


@router.get("/offer-intelligence")
async def offer_intelligence(
    period: str = Query("week"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    network_id: Optional[int] = Query(None),
    account_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    """Offer+brand performance across all networks/accounts with optional network/account filter."""
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            CampaignMapping.network_campaign_name.label("offer_name"),
            AffiliateStat.sub_id1.label("brand"),
            AffiliateAccount.id.label("account_id"),
            AffiliateAccount.label.label("account_label"),
            AffiliateNetwork.id.label("network_id"),
            AffiliateNetwork.name.label("network_name"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
            func.min(AffiliateStat.stat_date).label("first_seen"),
            func.max(AffiliateStat.stat_date).label("last_seen"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(AffiliateAccount, CampaignMapping.account_id == AffiliateAccount.id)
        .join(AffiliateNetwork, AffiliateAccount.network_id == AffiliateNetwork.id)
        .where(
            AffiliateStat.stat_date >= start,
            AffiliateStat.stat_date <= end,
            AffiliateAccount.active == True,
            AffiliateNetwork.active == True,
        )
        .group_by(
            CampaignMapping.network_campaign_name,
            AffiliateStat.sub_id1,
            AffiliateAccount.id,
            AffiliateAccount.label,
            AffiliateNetwork.id,
            AffiliateNetwork.name,
        )
    )

    if network_id is not None:
        q = q.where(AffiliateNetwork.id == network_id)
    if account_id is not None:
        q = q.where(AffiliateAccount.id == account_id)

    result = await db.execute(q)
    rows = result.all()

    # Merge into offer+brand+network groups; aggregate across accounts within same network
    groups: dict = {}
    for r in rows:
        key = (r.offer_name, r.brand, r.network_id)
        if key not in groups:
            groups[key] = {
                "offer_name": r.offer_name,
                "brand": r.brand,
                "network_id": r.network_id,
                "network_name": r.network_name,
                "revenue": 0.0,
                "clicks": 0,
                "conversions": 0,
                "first_seen": r.first_seen,
                "last_seen": r.last_seen,
                "accounts": [],
            }
        g = groups[key]
        g["revenue"] += float(r.revenue)
        g["clicks"] += int(r.clicks)
        g["conversions"] += int(r.conversions)
        if r.first_seen and (g["first_seen"] is None or r.first_seen < g["first_seen"]):
            g["first_seen"] = r.first_seen
        if r.last_seen and (g["last_seen"] is None or r.last_seen > g["last_seen"]):
            g["last_seen"] = r.last_seen
        g["accounts"].append({
            "account_id": r.account_id,
            "account_label": r.account_label,
            "network_name": r.network_name,
            "revenue": float(r.revenue),
            "clicks": int(r.clicks),
            "conversions": int(r.conversions),
        })

    sorted_groups = sorted(groups.values(), key=lambda x: x["revenue"], reverse=True)

    return [
        {
            "offer_name": g["offer_name"],
            "brand": g["brand"],
            "network_id": g["network_id"],
            "network_name": g["network_name"],
            "revenue": round(g["revenue"], 2),
            "clicks": g["clicks"],
            "conversions": g["conversions"],
            "epc": round(g["revenue"] / g["clicks"] * 100, 4) if g["clicks"] else 0.0,
            "first_seen": str(g["first_seen"]) if g["first_seen"] else None,
            "last_seen": str(g["last_seen"]) if g["last_seen"] else None,
            "account_count": len(g["accounts"]),
            "accounts": g["accounts"],
        }
        for g in sorted_groups
    ]


# ---------------------------------------------------------------------------
# Joe Sub-ID Stats Endpoint
# ---------------------------------------------------------------------------
from backend.models.joe_subid import JoeSubIdStat


@router.get("/joe-subids")
async def joe_subids(
    period: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role),
):
    """
    Return Joe's unique Sub IDs with aggregated stats for the requested period.
    Includes per-account breakdown and day-by-day detail rows.
    """
    start, end = get_date_range(period, start_date, end_date)

    q = (
        select(
            JoeSubIdStat.sub_id_value,
            AffiliateAccount.id.label("account_id"),
            AffiliateAccount.label.label("account_label"),
            AffiliateNetwork.name.label("network_name"),
            JoeSubIdStat.stat_date,
            JoeSubIdStat.revenue,
            JoeSubIdStat.clicks,
            JoeSubIdStat.conversions,
            JoeSubIdStat.offer_name,
        )
        .join(AffiliateAccount, JoeSubIdStat.account_id == AffiliateAccount.id)
        .join(AffiliateNetwork, AffiliateAccount.network_id == AffiliateNetwork.id)
        .where(
            and_(
                JoeSubIdStat.stat_date >= start,
                JoeSubIdStat.stat_date <= end,
            )
        )
        .order_by(JoeSubIdStat.stat_date.asc())
    )

    if search:
        q = q.where(JoeSubIdStat.sub_id_value.ilike(f"%{search}%"))

    result = await db.execute(q)
    rows = result.all()

    # Group by sub_id_value
    groups: dict = {}
    for r in rows:
        key = r.sub_id_value
        if key not in groups:
            groups[key] = {
                "sub_id": r.sub_id_value,
                "revenue": 0.0,
                "clicks": 0,
                "conversions": 0,
                "offer_names": set(),
                "first_seen": r.stat_date,
                "last_seen": r.stat_date,
                "accounts": {},
                "days": [],
            }
        g = groups[key]
        g["revenue"] += float(r.revenue)
        g["clicks"] += int(r.clicks)
        g["conversions"] += int(r.conversions)
        if r.offer_name:
            g["offer_names"].add(r.offer_name)
        if r.stat_date < g["first_seen"]:
            g["first_seen"] = r.stat_date
        if r.stat_date > g["last_seen"]:
            g["last_seen"] = r.stat_date

        # Per-account aggregate
        acc_key = r.account_id
        if acc_key not in g["accounts"]:
            g["accounts"][acc_key] = {
                "account_id": r.account_id,
                "account_label": r.account_label,
                "network_name": r.network_name,
                "revenue": 0.0,
                "clicks": 0,
                "conversions": 0,
            }
        g["accounts"][acc_key]["revenue"] += float(r.revenue)
        g["accounts"][acc_key]["clicks"] += int(r.clicks)
        g["accounts"][acc_key]["conversions"] += int(r.conversions)

        # Day-level detail
        g["days"].append({
            "date": str(r.stat_date),
            "account_label": r.account_label,
            "network_name": r.network_name,
            "revenue": float(r.revenue),
            "clicks": int(r.clicks),
            "conversions": int(r.conversions),
            "offer_name": r.offer_name,
        })

    sorted_groups = sorted(groups.values(), key=lambda x: x["revenue"], reverse=True)

    return [
        {
            "sub_id": g["sub_id"],
            "revenue": round(g["revenue"], 2),
            "clicks": g["clicks"],
            "conversions": g["conversions"],
            "epc": round(g["revenue"] / g["clicks"] * 100, 4) if g["clicks"] else 0.0,
            "offer_names": sorted(g["offer_names"]),
            "first_seen": str(g["first_seen"]),
            "last_seen": str(g["last_seen"]),
            "accounts": list(g["accounts"].values()),
            "days": sorted(g["days"], key=lambda d: d["date"]),
        }
        for g in sorted_groups
    ]
