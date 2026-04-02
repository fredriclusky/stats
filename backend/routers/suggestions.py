from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.ai_service import get_ai_suggestions
from backend.routers.auth import require_admin

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("")
async def ai_suggestions(
    lookback_days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin)
):
    return await get_ai_suggestions(db=db, lookback_days=lookback_days)
