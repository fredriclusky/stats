from fastapi import APIRouter, Depends
from backend.routers.auth import require_admin

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("")
async def schedule_placeholder(_=Depends(require_admin)):
    return {
        "status": "coming_soon",
        "message": "AI-powered mailing schedule optimization is coming soon. "
                   "This will analyze your campaign performance, mailing events, and "
                   "affiliate data to suggest optimal send times, lists, and campaigns.",
        "planned_features": [
            "AI-suggested send schedule based on conversion patterns",
            "List performance scoring",
            "Campaign rotation recommendations",
            "Revenue-maximizing daily/weekly schedule",
        ]
    }
