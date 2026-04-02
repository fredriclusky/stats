from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.affiliate import AffiliateNetwork, AffiliateAccount
from backend.routers.auth import require_admin

router = APIRouter(prefix="/api/affiliates", tags=["affiliates"])


class NetworkCreate(BaseModel):
    name: str
    network_type: str  # hasoffers, everflow, custom


class AccountCreate(BaseModel):
    network_id: int
    label: str
    api_key: str
    api_base_url: Optional[str] = None
    network_id_value: Optional[str] = None
    config_json: Optional[dict] = {}


# --- Networks ---
@router.get("/networks")
async def list_networks(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(AffiliateNetwork).where(AffiliateNetwork.active == True))
    networks = result.scalars().all()
    return [{"id": n.id, "name": n.name, "type": n.network_type, "created_at": n.created_at} for n in networks]


@router.post("/networks")
async def create_network(data: NetworkCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    network = AffiliateNetwork(name=data.name, network_type=data.network_type)
    db.add(network)
    await db.commit()
    await db.refresh(network)
    return {"id": network.id, "name": network.name, "type": network.network_type}


@router.delete("/networks/{network_id}")
async def delete_network(network_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(AffiliateNetwork).where(AffiliateNetwork.id == network_id))
    network = result.scalar_one_or_none()
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    network.active = False
    await db.commit()
    return {"ok": True}


# --- Accounts ---
@router.get("/accounts")
async def list_accounts(network_id: Optional[int] = None, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    q = select(AffiliateAccount).where(AffiliateAccount.active == True)
    if network_id:
        q = q.where(AffiliateAccount.network_id == network_id)
    result = await db.execute(q)
    accounts = result.scalars().all()
    return [
        {
            "id": a.id, "network_id": a.network_id, "label": a.label,
            "api_base_url": a.api_base_url, "network_id_value": a.network_id_value,
            "active": a.active, "created_at": a.created_at
        }
        for a in accounts
    ]


@router.post("/accounts")
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    account = AffiliateAccount(
        network_id=data.network_id, label=data.label, api_key=data.api_key,
        api_base_url=data.api_base_url, network_id_value=data.network_id_value,
        config_json=data.config_json or {}
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return {"id": account.id, "label": account.label}


@router.put("/accounts/{account_id}")
async def update_account(account_id: int, data: AccountCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(AffiliateAccount).where(AffiliateAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.label = data.label
    account.api_key = data.api_key
    account.api_base_url = data.api_base_url
    account.network_id_value = data.network_id_value
    account.config_json = data.config_json or {}
    await db.commit()
    return {"ok": True}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(AffiliateAccount).where(AffiliateAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.active = False
    await db.commit()
    return {"ok": True}


# --- Test connection ---
@router.get("/accounts/{account_id}/test")
async def test_account_connection(account_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Test that the API credentials for an account are valid."""
    from backend.adapters import get_adapter
    from backend.models.affiliate import AffiliateNetwork

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
        return {"ok": True, "message": f"Connected successfully. Found {len(campaigns)} active campaigns.", "campaign_count": len(campaigns)}
    except Exception as e:
        return {"ok": False, "message": str(e)}
