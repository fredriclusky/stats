from datetime import timedelta, datetime
import datetime as _dt
import zoneinfo

_EASTERN = zoneinfo.ZoneInfo("America/New_York")

def _today_eastern():
    return _dt.datetime.now(_EASTERN).date()
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.database import AsyncSessionLocal
from backend.models.affiliate import AffiliateAccount, AffiliateNetwork
from backend.models.campaign import Campaign, CampaignMapping
from backend.models.stats import AffiliateStat
from backend.models.joe_subid import JoeSubIdStat
from backend.adapters import get_adapter

logger = logging.getLogger(__name__)


async def _get_or_create_mapping(db: AsyncSession, account_id: int, campaign_id: str, campaign_name: str) -> int:
    result = await db.execute(
        select(CampaignMapping).where(
            and_(
                CampaignMapping.account_id == account_id,
                CampaignMapping.network_campaign_id == campaign_id,
            )
        )
    )
    mapping = result.scalar_one_or_none()
    if mapping:
        return mapping.id

    clean_name = (campaign_name or "").strip() or f"Offer {campaign_id}"
    result = await db.execute(select(Campaign).where(Campaign.name == clean_name))
    canon = result.scalar_one_or_none()

    if not canon:
        canon = Campaign(name=clean_name, notes=f"Auto-created from network offer {campaign_id}")
        db.add(canon)
        await db.flush()

    mapping = CampaignMapping(
        campaign_id=canon.id,
        account_id=account_id,
        network_campaign_id=campaign_id,
        network_campaign_name=clean_name,
    )
    db.add(mapping)
    await db.flush()
    logger.info(f"Auto-created mapping: offer {campaign_id} ({clean_name}) → campaign {canon.id}")
    return mapping.id


async def sync_account(account: AffiliateAccount, network_type: str, days_back: int = 1):
    """Pull stats for an account and upsert into affiliate_stats."""
    try:
        adapter = get_adapter(
            network_type=network_type,
            api_key=account.api_key,
            api_base_url=account.api_base_url,
            network_id_value=account.network_id_value,
            config=account.config_json or {}
        )
    except ValueError as e:
        logger.error(f"Cannot create adapter for account {account.id} ({account.label}): {e}")
        return 0

    end_date = _today_eastern()
    start_date = end_date - timedelta(days=days_back)

    try:
        stats = await adapter.get_stats(start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error(f"Failed to sync account {account.id} ({account.label}): {e}")
        return 0

    synced = 0
    async with AsyncSessionLocal() as db:
        for row in stats:
            campaign_id = str(row.get("campaign_id", "")).strip()
            if not campaign_id:
                continue

            stat_date = row.get("date")
            if isinstance(stat_date, str):
                try:
                    stat_date = datetime.strptime(stat_date, "%Y-%m-%d").date()
                except Exception:
                    continue

            mapping_id = await _get_or_create_mapping(
                db, account.id, campaign_id, row.get("campaign_name", "")
            )

            sub_id = row.get("sub_id")    # affiliate_info2 — Joe's Sub ID
            sub_id1 = row.get("sub_id1")  # affiliate_info1 — campaign identifier

            existing = await db.execute(
                select(AffiliateStat).where(
                    and_(
                        AffiliateStat.campaign_mapping_id == mapping_id,
                        AffiliateStat.stat_date == stat_date,
                        AffiliateStat.sub_id == sub_id,
                        AffiliateStat.sub_id1 == sub_id1,
                    )
                )
            )
            stat_obj = existing.scalars().first()

            if stat_obj:
                stat_obj.clicks = row.get("clicks", 0)
                stat_obj.conversions = row.get("conversions", 0)
                stat_obj.revenue = row.get("revenue", 0)
                stat_obj.payout = row.get("payout", 0)
                stat_obj.raw_json = row.get("raw", {})
            else:
                stat_obj = AffiliateStat(
                    campaign_mapping_id=mapping_id,
                    stat_date=stat_date,
                    clicks=row.get("clicks", 0),
                    conversions=row.get("conversions", 0),
                    revenue=row.get("revenue", 0),
                    payout=row.get("payout", 0),
                    sub_id=sub_id,
                    sub_id1=sub_id1,
                    raw_json=row.get("raw", {})
                )
                db.add(stat_obj)
            synced += 1

        await db.commit()
    logger.info(f"Synced {synced} stats rows for account {account.label}")
    return synced


async def sync_joe_subids(account: AffiliateAccount, network_type: str, days_back: int = 1):
    """
    Pull Joe's unique Sub IDs for an account and upsert into joe_sub_id_stats.
    HasOffers groups by affiliate_info2; Everflow groups by sub1.
    """
    try:
        adapter = get_adapter(
            network_type=network_type,
            api_key=account.api_key,
            api_base_url=account.api_base_url,
            network_id_value=account.network_id_value,
            config=account.config_json or {}
        )
    except ValueError as e:
        logger.error(f"Cannot create adapter for account {account.id} ({account.label}): {e}")
        return 0

    if not hasattr(adapter, "get_joe_sub_ids"):
        logger.debug(f"Adapter for {account.label} does not support get_joe_sub_ids — skipping")
        return 0

    end_date = _today_eastern()
    start_date = end_date - timedelta(days=days_back)

    try:
        rows = await adapter.get_joe_sub_ids(start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error(f"Failed to sync Joe sub-IDs for account {account.id} ({account.label}): {e}")
        return 0

    synced = 0
    async with AsyncSessionLocal() as db:
        for row in rows:
            sub_id_value = (row.get("sub_id_value") or "").strip()
            if not sub_id_value:
                continue

            stat_date = row.get("date")
            if isinstance(stat_date, str):
                try:
                    from datetime import date as _date
                    stat_date = datetime.strptime(stat_date, "%Y-%m-%d").date()
                except Exception:
                    continue
            if stat_date is None:
                continue

            existing = await db.execute(
                select(JoeSubIdStat).where(
                    and_(
                        JoeSubIdStat.account_id == account.id,
                        JoeSubIdStat.stat_date == stat_date,
                        JoeSubIdStat.sub_id_value == sub_id_value,
                    )
                )
            )
            obj = existing.scalars().first()

            if obj:
                obj.revenue = row.get("revenue", 0)
                obj.clicks = row.get("clicks", 0)
                obj.conversions = row.get("conversions", 0)
                obj.offer_name = row.get("campaign_name") or obj.offer_name
                obj.synced_at = datetime.utcnow()
            else:
                obj = JoeSubIdStat(
                    account_id=account.id,
                    stat_date=stat_date,
                    sub_id_value=sub_id_value,
                    revenue=row.get("revenue", 0),
                    clicks=row.get("clicks", 0),
                    conversions=row.get("conversions", 0),
                    offer_name=row.get("campaign_name"),
                )
                db.add(obj)
            synced += 1

        await db.commit()
    logger.info(f"Synced {synced} Joe sub-ID rows for account {account.label}")
    return synced


async def sync_all_accounts(days_back: int = 1):
    """Sync all active affiliate accounts."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AffiliateAccount, AffiliateNetwork.network_type)
            .join(AffiliateNetwork, AffiliateAccount.network_id == AffiliateNetwork.id)
            .where(AffiliateAccount.active == True, AffiliateNetwork.active == True)
        )
        accounts = result.all()

    total = 0
    for account, network_type in accounts:
        count = await sync_account(account, network_type, days_back=days_back)
        await sync_joe_subids(account, network_type, days_back=days_back)
        total += count
    logger.info(f"Total sync complete: {total} rows across {len(accounts)} accounts")
    return total
