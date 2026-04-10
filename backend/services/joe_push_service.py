"""
Joe Push Service
----------------
After each sync, aggregate total revenue per sub_id from joe_sub_id_stats,
compare against last pushed value, and POST only changed sub_ids to Joe's webhook.

Payload sent per changed sub_id:
    POST <JOE_WEBHOOK_URL>
    Authorization: Bearer <JOE_API_KEY>
    Content-Type: application/json
    { "sub_id": "LIST1234", "revenue": 84.50 }
"""
import logging
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models.joe_subid import JoeSubIdStat
from backend.models.joe_push_log import JoePushLog
from backend.config import get_settings

logger = logging.getLogger(__name__)


async def push_joe_updates() -> dict:
    """
    Aggregate total revenue per sub_id for the last 60 days,
    then push any sub_id whose revenue has changed since last send.
    Returns a summary dict.
    """
    settings = get_settings()
    webhook_url = settings.joe_webhook_url
    api_key = settings.joe_api_key

    if not webhook_url:
        logger.debug("JOE_WEBHOOK_URL not configured — skipping Joe push")
        return {"skipped": True, "reason": "JOE_WEBHOOK_URL not set"}

    # Window: last 60 days rolling so revenue is always fresh
    today = datetime.now().date()
    since = today - timedelta(days=60)

    async with AsyncSessionLocal() as db:
        # Aggregate current total revenue per sub_id
        result = await db.execute(
            select(
                JoeSubIdStat.sub_id_value,
                func.sum(JoeSubIdStat.revenue).label("total_revenue"),
            )
            .where(JoeSubIdStat.stat_date >= since)
            .group_by(JoeSubIdStat.sub_id_value)
        )
        current_totals = {row.sub_id_value: float(row.total_revenue or 0) for row in result}

        # Load last-sent values for all known sub_ids
        log_result = await db.execute(select(JoePushLog))
        push_logs = {r.sub_id_value: r for r in log_result.scalars().all()}

    pushed = 0
    skipped = 0
    errors = 0
    changed_ids = []

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    for sub_id, revenue in current_totals.items():
        last_log = push_logs.get(sub_id)
        last_sent = float(last_log.last_sent_revenue) if last_log else None

        # Only push if revenue changed (or never sent before)
        if last_sent is not None and abs(revenue - last_sent) < 0.01:
            skipped += 1
            continue

        changed_ids.append(sub_id)
        payload = {"sub_id": sub_id, "revenue": round(revenue, 2)}
        error_msg = None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload, headers=headers)
                resp.raise_for_status()
            pushed += 1
            logger.info(f"Pushed sub_id {sub_id}: ${revenue:.2f} (was ${last_sent})")
        except Exception as e:
            errors += 1
            error_msg = str(e)[:500] or f"{type(e).__name__}"
            logger.error(f"Failed to push sub_id {sub_id}: {e}")

        # Update the push log regardless of success/failure (to track errors)
        async with AsyncSessionLocal() as db:
            log_obj = push_logs.get(sub_id)
            if log_obj:
                # Re-fetch within this session
                result = await db.execute(
                    select(JoePushLog).where(JoePushLog.sub_id_value == sub_id)
                )
                log_obj = result.scalar_one_or_none()

            if log_obj:
                if not error_msg:
                    log_obj.last_sent_revenue = revenue
                    log_obj.push_count = (log_obj.push_count or 0) + 1
                    log_obj.last_pushed_at = datetime.utcnow()
                log_obj.last_error = error_msg
            else:
                log_obj = JoePushLog(
                    sub_id_value=sub_id,
                    last_sent_revenue=revenue if not error_msg else 0,
                    push_count=1 if not error_msg else 0,
                    last_pushed_at=datetime.utcnow() if not error_msg else None,
                    last_error=error_msg,
                )
                db.add(log_obj)
            await db.commit()

    summary = {
        "total_sub_ids": len(current_totals),
        "pushed": pushed,
        "skipped_unchanged": skipped,
        "errors": errors,
    }
    logger.info(f"Joe push complete: {summary}")
    return summary
