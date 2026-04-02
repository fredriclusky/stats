from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.config import get_settings
from backend.routers.stats import get_summary, stats_by_campaign, stats_daily
from backend.routers.auth import get_current_user, require_any_role
from backend.models.user import User

router = APIRouter(prefix="/api/partner", tags=["partner"])
settings = get_settings()


async def require_partner_access(
    token: str = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Allow access via JWT (partner role) or secret token."""
    if token and token == settings.partner_token:
        return {"role": "partner", "via": "token"}
    if current_user and current_user.role in ("admin", "partner"):
        return {"role": current_user.role, "via": "jwt"}
    raise HTTPException(status_code=403, detail="Partner access denied")


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
