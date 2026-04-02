from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.mailing import MailingEvent
from backend.models.subid import SubID
from backend.config import get_settings

router = APIRouter(prefix="/api/inbound", tags=["inbound"])
settings = get_settings()


class MailingEventIn(BaseModel):
    sub_id: str
    prompt_used: Optional[str] = None
    list_used: Optional[str] = None
    sends: Optional[int] = None
    opens: Optional[int] = None
    clicks: Optional[int] = None
    extra_data: Optional[dict] = {}


@router.post("")
async def receive_mailing_event(
    data: MailingEventIn,
    db: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    # Lookup sub_id in registry
    sub_id_ref = None
    result = await db.execute(select(SubID).where(SubID.value == data.sub_id))
    sub_id_obj = result.scalar_one_or_none()

    if sub_id_obj:
        sub_id_obj.last_seen_at = datetime.utcnow()
        sub_id_ref = sub_id_obj.id

    event = MailingEvent(
        sub_id_id=sub_id_ref,
        sub_id_value=data.sub_id,
        prompt_used=data.prompt_used,
        list_used=data.list_used,
        sends=data.sends,
        opens=data.opens,
        clicks=data.clicks,
        extra_data=data.extra_data or {},
    )
    db.add(event)
    await db.commit()
    return {"ok": True, "event_id": event.id}


@router.get("/events")
async def list_events(
    limit: int = 50,
    sub_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    from backend.routers.auth import oauth2_scheme
    q = select(MailingEvent).order_by(MailingEvent.received_at.desc()).limit(limit)
    if sub_id:
        q = q.where(MailingEvent.sub_id_value == sub_id)
    result = await db.execute(q)
    events = result.scalars().all()
    return [
        {
            "id": e.id, "sub_id": e.sub_id_value, "prompt_used": e.prompt_used,
            "list_used": e.list_used, "sends": e.sends, "opens": e.opens,
            "clicks": e.clicks, "extra_data": e.extra_data, "received_at": e.received_at
        }
        for e in events
    ]
