from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.campaign import Campaign, CampaignMapping
from backend.models.affiliate import AffiliateAccount, AffiliateNetwork
from backend.routers.auth import require_admin
from backend.adapters import get_adapter

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    notes: Optional[str] = None
    tags: Optional[str] = None


class MappingCreate(BaseModel):
    campaign_id: int
    account_id: int
    network_campaign_id: str
    network_campaign_name: Optional[str] = None
    extra_data: Optional[dict] = {}


@router.get("")
async def list_campaigns(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    campaigns = result.scalars().all()
    return [{"id": c.id, "name": c.name, "notes": c.notes, "tags": c.tags, "created_at": c.created_at} for c in campaigns]


@router.post("")
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    campaign = Campaign(name=data.name, notes=data.notes, tags=data.tags)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"id": campaign.id, "name": campaign.name}


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, data: CampaignCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.name = data.name
    campaign.notes = data.notes
    campaign.tags = data.tags
    await db.commit()
    return {"ok": True}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(campaign)
    await db.commit()
    return {"ok": True}


# --- Discover campaigns from live network API ---
@router.get("/discover/{account_id}")
async def discover_campaigns(account_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Fetch live campaigns from the affiliate network for this account."""
    result = await db.execute(
        select(AffiliateAccount, AffiliateNetwork.network_type)
        .join(AffiliateNetwork, AffiliateAccount.network_id == AffiliateNetwork.id)
        .where(AffiliateAccount.id == account_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")

    account, network_type = row
    try:
        adapter = get_adapter(
            network_type=network_type,
            api_key=account.api_key,
            api_base_url=account.api_base_url,
            network_id_value=account.network_id_value,
            config=account.config_json or {}
        )
        campaigns = await adapter.get_campaigns()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch campaigns from network: {str(e)}")

    # Mark which ones are already mapped for this account
    mapped_result = await db.execute(
        select(CampaignMapping).where(CampaignMapping.account_id == account_id)
    )
    already_mapped = {m.network_campaign_id for m in mapped_result.scalars().all()}

    return [
        {**c, "already_mapped": c["id"] in already_mapped}
        for c in campaigns
    ]


# --- Mappings ---
@router.get("/{campaign_id}/mappings")
async def list_mappings(campaign_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(CampaignMapping).where(CampaignMapping.campaign_id == campaign_id))
    mappings = result.scalars().all()
    return [
        {
            "id": m.id, "campaign_id": m.campaign_id, "account_id": m.account_id,
            "network_campaign_id": m.network_campaign_id,
            "network_campaign_name": m.network_campaign_name,
            "created_at": m.created_at
        }
        for m in mappings
    ]


@router.post("/mappings")
async def create_mapping(data: MappingCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    mapping = CampaignMapping(
        campaign_id=data.campaign_id, account_id=data.account_id,
        network_campaign_id=data.network_campaign_id,
        network_campaign_name=data.network_campaign_name,
        extra_data=data.extra_data or {}
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return {"id": mapping.id}


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(CampaignMapping).where(CampaignMapping.id == mapping_id))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await db.delete(mapping)
    await db.commit()
    return {"ok": True}
