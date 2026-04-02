from datetime import date, timedelta
from typing import Optional
import logging
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.models.stats import AffiliateStat
from backend.models.campaign import Campaign, CampaignMapping
from backend.models.mailing import MailingEvent
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_campaign_performance_summary(db: AsyncSession, lookback_days: int = 90) -> str:
    """Build a text summary of campaign performance to feed to the LLM."""
    end = date.today()
    start = end - timedelta(days=lookback_days)
    recent_end = end
    recent_start = end - timedelta(days=30)
    older_start = end - timedelta(days=lookback_days)
    older_end = end - timedelta(days=31)

    q = (
        select(
            Campaign.name.label("name"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
            func.coalesce(func.sum(AffiliateStat.conversions), 0).label("conversions"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(Campaign, CampaignMapping.campaign_id == Campaign.id)
        .where(AffiliateStat.stat_date >= start, AffiliateStat.stat_date <= end)
        .group_by(Campaign.name)
        .order_by(func.sum(AffiliateStat.revenue).desc())
    )
    result = await db.execute(q)
    all_rows = result.all()

    # Recent performance (last 30 days)
    q_recent = (
        select(
            Campaign.name.label("name"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(Campaign, CampaignMapping.campaign_id == Campaign.id)
        .where(AffiliateStat.stat_date >= recent_start, AffiliateStat.stat_date <= recent_end)
        .group_by(Campaign.name)
    )
    result_recent = await db.execute(q_recent)
    recent_map = {r.name: float(r.revenue) for r in result_recent.all()}

    # Older performance (31-90 days ago)
    q_older = (
        select(
            Campaign.name.label("name"),
            func.coalesce(func.sum(AffiliateStat.revenue), 0).label("revenue"),
        )
        .join(CampaignMapping, AffiliateStat.campaign_mapping_id == CampaignMapping.id)
        .join(Campaign, CampaignMapping.campaign_id == Campaign.id)
        .where(AffiliateStat.stat_date >= older_start, AffiliateStat.stat_date <= older_end)
        .group_by(Campaign.name)
    )
    result_older = await db.execute(q_older)
    older_map = {r.name: float(r.revenue) for r in result_older.all()}

    lines = [f"Campaign performance summary (last {lookback_days} days):\n"]
    for row in all_rows:
        recent = recent_map.get(row.name, 0)
        older = older_map.get(row.name, 0)
        trend = ""
        if older > 0 and recent < older * 0.5:
            trend = " [FALLING - was stronger 31-90 days ago]"
        elif older > 0 and recent > older * 1.5:
            trend = " [RISING]"
        elif older > 10 and recent < 1:
            trend = " [INACTIVE - was previously successful]"
        lines.append(
            f"- {row.name}: Total revenue=${float(row.revenue):.2f}, "
            f"conversions={int(row.conversions)}, last30d=${recent:.2f}, prev60d=${older:.2f}{trend}"
        )

    # Recent mailing events
    q_mail = select(MailingEvent).order_by(MailingEvent.received_at.desc()).limit(20)
    result_mail = await db.execute(q_mail)
    events = result_mail.scalars().all()
    if events:
        lines.append("\nRecent mailing sends:")
        for e in events:
            lines.append(f"- sub_id={e.sub_id_value}, list={e.list_used}, prompt_snippet={str(e.prompt_used or '')[:80]}")

    return "\n".join(lines)


async def get_ai_suggestions(db: AsyncSession, lookback_days: int = 90) -> dict:
    """Ask GPT-4 for campaign recommendations based on performance data."""
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-your"):
        return {
            "suggestions": "OpenAI API key not configured. Add your key to /opt/stats-tool/.env under OPENAI_API_KEY.",
            "raw_context": ""
        }

    context = await get_campaign_performance_summary(db, lookback_days=lookback_days)

    system_prompt = """You are an expert email marketing analyst and affiliate campaign strategist.
You analyze mailing campaign performance data and provide actionable recommendations.
Focus on: revenue trends, campaigns worth reviving, what to keep running, what to pause.
Be specific, concise, and data-driven."""

    user_prompt = f"""Based on this campaign performance data, provide:
1. Top 3 campaigns to prioritize right now and why
2. Campaigns that fell off but were successful - worth retrying?
3. Any campaigns to consider pausing
4. Overall strategic suggestion for maximizing revenue this month

{context}"""

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )

    return {
        "suggestions": response.choices[0].message.content,
        "raw_context": context,
        "model": response.model,
        "tokens_used": response.usage.total_tokens
    }
