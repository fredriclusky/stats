from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.database import get_db
from backend.config import get_settings
from backend.routers.stats import get_date_range, get_summary, stats_by_campaign, stats_daily
from backend.routers.auth import get_current_user, require_any_role
from backend.models.user import User
from backend.models.stats import AffiliateStat
from backend.models.campaign import CampaignMapping
from backend.models.affiliate import AffiliateAccount, AffiliateNetwork

router = APIRouter(prefix="/api/partner", tags=["partner"])
settings = get_settings()


async def require_karlin_access(current_user: User = Depends(get_current_user)):
    """Allow admins or the dedicated Karlin partner user."""
    if current_user.role == "admin" or current_user.username.lower() == "karlin":
        return current_user
    raise HTTPException(status_code=403, detail="Karlin access denied")


# Legacy partner endpoints retained for compatibility.
@router.get("/summary")
async def partner_summary(
    period: str = Query("today"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role)
):
    return await get_summary(period=period, db=db, _=_)


@router.get("/by-campaign")
async def partner_by_campaign(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role)
):
    return await stats_by_campaign(period=period, db=db, _=_)


@router.get("/daily")
async def partner_daily(
    period: str = Query("month"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_any_role)
):
    return await stats_daily(period=period, db=db, _=_)


@router.get("/karlin/summary")
async def karlin_summary(
    period: str = Query("today", enum=["today", "yesterday", "week", "month", "year", "custom"]),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_karlin_access),
):
    start, end = get_date_range(period, start_date, end_date)
    result = await db.execute(
        select(
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(AffiliateAccount, CampaignMapping.account_id == AffiliateAccount.id)
        .where(
            and_(
                AffiliateStat.stat_date >= start,
                AffiliateStat.stat_date <= end,
                AffiliateAccount.active == True,
                AffiliateAccount.label.ilike("%Karlin%"),
            )
        )
    )
    row = result.one()
    return {
        "period": period,
        "start": str(start),
        "end": str(end),
        "revenue": float(row.revenue),
        "clicks": int(row.clicks),
        "conversions": int(row.conversions),
    }


@router.get("/karlin/by-account")
async def karlin_by_account(
    period: str = Query("today"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_karlin_access),
):
    start, end = get_date_range(period, start_date, end_date)
    result = await db.execute(
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
            ),
        )
        .where(
            AffiliateAccount.active == True,
            AffiliateNetwork.active == True,
            AffiliateAccount.label.ilike("%Karlin%"),
        )
        .group_by(AffiliateAccount.id, AffiliateAccount.label, AffiliateNetwork.name)
        .order_by(func.coalesce(func.sum(AffiliateStat.revenue), 0).desc())
    )
    rows = result.all()
    return [
        {
            "account_id": r.account_id,
            "account_label": r.account_label,
            "network_name": r.network_name,
            "revenue": float(r.revenue),
            "clicks": int(r.clicks),
            "conversions": int(r.conversions),
        }
        for r in rows
    ]


@router.get("/karlin/daily")
async def karlin_daily(
    period: str = Query("month"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_karlin_access),
):
    start, end = get_date_range(period, start_date, end_date)
    result = await db.execute(
        select(
            AffiliateStat.stat_date.label("stat_date"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.clicks), 0).label("clicks"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(AffiliateAccount, CampaignMapping.account_id == AffiliateAccount.id)
        .where(
            AffiliateStat.stat_date >= start,
            AffiliateStat.stat_date <= end,
            AffiliateAccount.active == True,
            AffiliateAccount.label.ilike("%Karlin%"),
        )
        .group_by(AffiliateStat.stat_date)
        .order_by(AffiliateStat.stat_date)
    )
    rows = result.all()
    return [
        {
            "date": str(r.stat_date),
            "revenue": float(r.revenue),
            "clicks": int(r.clicks),
            "conversions": int(r.conversions),
        }
        for r in rows
    ]
