from fastapi import APIRouter, Depends, BackgroundTasks, Query
from apscheduler.triggers.interval import IntervalTrigger
from backend.routers.auth import require_admin
from backend.services.sync_service import sync_all_accounts
from backend.scheduler import scheduler

router = APIRouter(prefix="/api/sync", tags=["sync"])


async def _sync_and_reschedule(days_back: int):
    """Run the sync then immediately reset the 15-minute automatic timer."""
    await sync_all_accounts(days_back=days_back)
    try:
        scheduler.reschedule_job(
            "sync_affiliates",
            trigger=IntervalTrigger(minutes=15)
        )
    except Exception:
        pass  # Scheduler may not be running in test environments


@router.post("/now")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    days_back: int = Query(1, ge=1, le=90),
    _=Depends(require_admin)
):
    """Manually trigger a sync and reset the 15-minute auto-sync timer."""
    background_tasks.add_task(_sync_and_reschedule, days_back=days_back)
    return {"ok": True, "message": f"Sync triggered for last {days_back} day(s)"}
