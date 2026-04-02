from fastapi import APIRouter, Depends, BackgroundTasks, Query
from backend.routers.auth import require_admin
from backend.services.sync_service import sync_all_accounts

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/now")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    days_back: int = Query(1, ge=1, le=90),
    _=Depends(require_admin)
):
    """Manually trigger a sync of all affiliate accounts."""
    background_tasks.add_task(sync_all_accounts, days_back=days_back)
    return {"ok": True, "message": f"Sync triggered for last {days_back} day(s)"}
