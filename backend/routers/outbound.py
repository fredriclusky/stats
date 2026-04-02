from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from backend.database import get_db
from backend.models.subid import SubID
from backend.models.stats import AffiliateStat
from backend.models.campaign import CampaignMapping
from backend.models.affiliate import AffiliateAccount, AffiliateNetwork
from backend.models.mailing import OutboundLog
from backend.routers.auth import require_admin

router = APIRouter(prefix="/api/outbound", tags=["outbound"])


class SubIDCreate(BaseModel):
    value: str
    label: Optional[str] = None
    campaign_mapping_id: Optional[int] = None
    notes: Optional[str] = None


@router.get("/subids")
async def list_subids(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(SubID).order_by(SubID.issued_at.desc()))
    subids = result.scalars().all()
    return [
        {
            "id": s.id, "value": s.value, "label": s.label,
            "campaign_mapping_id": s.campaign_mapping_id,
            "notes": s.notes, "active": s.active,
            "issued_at": s.issued_at, "last_seen_at": s.last_seen_at
        }
        for s in subids
    ]


@router.post("/subids")
async def create_subid(data: SubIDCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    subid = SubID(
        value=data.value, label=data.label,
        campaign_mapping_id=data.campaign_mapping_id,
        notes=data.notes
    )
    db.add(subid)
    await db.commit()
    await db.refresh(subid)
    return {"id": subid.id, "value": subid.value}


@router.put("/subids/{subid_id}")
async def update_subid(subid_id: int, data: SubIDCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from fastapi import HTTPException
    result = await db.execute(select(SubID).where(SubID.id == subid_id))
    subid = result.scalar_one_or_none()
    if not subid:
        raise HTTPException(status_code=404, detail="SubID not found")
    subid.label = data.label
    subid.campaign_mapping_id = data.campaign_mapping_id
    subid.notes = data.notes
    await db.commit()
    return {"ok": True}


@router.get("/revenue")
async def get_revenue_for_subid(
    sub_id: str = Query(..., description="Joe's Sub ID 2 value (affiliate_info2)"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint Joe's system uses to fetch revenue for a Sub ID.
    Queries all active HasOffers and Everflow accounts live for accurate sub2 data.
    """
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    from backend.adapters import get_adapter

    # Fetch all active accounts
    result = await db.execute(
        select(AffiliateAccount, AffiliateNetwork.network_type)
        .join(AffiliateNetwork, AffiliateAccount.network_id == AffiliateNetwork.id)
        .where(AffiliateAccount.active == True, AffiliateNetwork.active == True)
    )
    accounts = result.all()

    total_revenue = 0.0
    breakdown = []

    for account, network_type in accounts:
        try:
            adapter = get_adapter(
                network_type=network_type,
                api_key=account.api_key,
                api_base_url=account.api_base_url,
                network_id_value=account.network_id_value,
                config=account.config_json or {}
            )
            rows = await adapter.get_sub_id_stats(
                sub_id=sub_id,
                start_date=start_date,
                end_date=end_date
            )
            acct_revenue = sum(r["revenue"] for r in rows)
            total_revenue += acct_revenue
            if acct_revenue > 0:
                breakdown.append({"account": account.label, "revenue": acct_revenue})
        except Exception:
            # Skip accounts that error — don't block Joe's query
            pass

    log = OutboundLog(sub_id_value=sub_id, revenue_sent=total_revenue)
    db.add(log)
    await db.commit()

    return {
        "sub_id": sub_id,
        "revenue": round(total_revenue, 2),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "breakdown": breakdown,
    }


@router.get("/log")
async def get_outbound_log(limit: int = 100, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(OutboundLog).order_by(OutboundLog.sent_at.desc()).limit(limit))
    logs = result.scalars().all()
    return [
        {"id": l.id, "sub_id": l.sub_id_value, "revenue_sent": float(l.revenue_sent or 0), "sent_at": l.sent_at}
        for l in logs
    ]
