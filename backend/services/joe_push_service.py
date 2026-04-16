"""
Joe Push Service
----------------
After each sync, calculate TODAY's revenue per sub_id from joe_sub_id_stats,
then push to Joe's webhook when:
  - It's a new day (last_sent_date != today) — always push the fresh daily total
  - OR revenue changed since last push within the same day

This keeps Joe's system in sync with our "today" dashboard view.

Payload:
    POST <JOE_WEBHOOK_URL>
    Authorization: Bearer <JOE_API_KEY>
    Content-Type: application/json
    { "sub_id": "LIST1234", "revenue": 84.50 }
"""
import logging
import zoneinfo
from datetime import datetime
import httpx
from sqlalchemy import select, func, and_

from backend.database import AsyncSessionLocal
from backend.models.joe_subid import JoeSubIdStat
from backend.models.joe_push_log import JoePushLog
from backend.config import get_settings

logger = logging.getLogger(__name__)
_EASTERN = zoneinfo.ZoneInfo("America/New_York")


def _today_est():
    return datetime.now(_EASTERN).date()


async def push_joe_updates() -> dict:
    """
    Push today's revenue per sub_id to Joe. Only fires when:
      - It's a new day (always send the fresh day total), OR
      - Revenue changed since last push within the same day.
    Skips sub_ids with $0 today.
    """
    settings = get_settings()
    webhook_url = settings.joe_webhook_url
    api_key = settings.joe_api_key

    if not webhook_url:
        logger.debug("JOE_WEBHOOK_URL not configured — skipping Joe push")
        return {"skipped": True, "reason": "JOE_WEBHOOK_URL not set"}

    today = _today_est()

    async with AsyncSessionLocal() as db:
        # Today's revenue only
        result = await db.execute(
            select(
                JoeSubIdStat.sub_id_value,
                func.sum(JoeSubIdStat.revenue).label("today_revenue"),
            )
            .where(JoeSubIdStat.stat_date == today)
            .group_by(JoeSubIdStat.sub_id_value)
        )
        current_totals = {
            row.sub_id_value: float(row.today_revenue or 0)
            for row in result
            if float(row.today_revenue or 0) > 0  # skip $0 sub-ids
        }

        log_result = await db.execute(select(JoePushLog))
        push_logs = {r.sub_id_value: r for r in log_result.scalars().all()}

    pushed = 0
    skipped = 0
    errors = 0

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    for sub_id, revenue in current_totals.items():
        last_log = push_logs.get(sub_id)
        last_sent_rev = float(last_log.last_sent_revenue) if last_log else None
        last_sent_date = last_log.last_sent_date if last_log else None

        # Skip only if: same day AND revenue unchanged (within 1 cent)
        same_day = (last_sent_date == today)
        rev_unchanged = (last_sent_rev is not None and abs(revenue - last_sent_rev) < 0.01)

        if same_day and rev_unchanged:
            skipped += 1
            continue

        payload = {"sub_id": sub_id, "revenue": round(revenue, 2)}
        error_msg = None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload, headers=headers)
                resp.raise_for_status()
            pushed += 1
            logger.info(
                f"Pushed sub_id {sub_id}: ${revenue:.2f} "
                f"(was ${last_sent_rev} on {last_sent_date}, today={today})"
            )
        except Exception as e:
            errors += 1
            error_msg = str(e)[:500] or f"{type(e).__name__}"
            logger.error(f"Failed to push sub_id {sub_id}: {e}")

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(JoePushLog).where(JoePushLog.sub_id_value == sub_id)
            )
            log_obj = result.scalar_one_or_none()

            if log_obj:
                if not error_msg:
                    log_obj.last_sent_revenue = revenue
                    log_obj.last_sent_date = today
                    log_obj.push_count = (log_obj.push_count or 0) + 1
                    log_obj.last_pushed_at = datetime.utcnow()
                log_obj.last_error = error_msg
            else:
                log_obj = JoePushLog(
                    sub_id_value=sub_id,
                    last_sent_revenue=revenue if not error_msg else 0,
                    last_sent_date=today if not error_msg else None,
                    push_count=1 if not error_msg else 0,
                    last_pushed_at=datetime.utcnow() if not error_msg else None,
                    last_error=error_msg,
                )
                db.add(log_obj)
            await db.commit()

    summary = {
        "date": str(today),
        "total_sub_ids_today": len(current_totals),
        "pushed": pushed,
        "skipped_unchanged": skipped,
        "errors": errors,
    }
    logger.info(f"Joe push complete: {summary}")
    return summary
