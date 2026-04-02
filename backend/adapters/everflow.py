from datetime import date, datetime
from typing import Optional
import httpx
from backend.adapters.base import BaseAdapter


class EverflowAdapter(BaseAdapter):
    """
    Everflow Affiliate API adapter.
    Docs: https://developers.everflow.io/docs/affiliate/

    Auth: X-Eflow-API-Key header with your affiliate API key.
    No network_id_value needed — the key is tied to your affiliate account.
    """

    DEFAULT_BASE = "https://api.eflow.team/v1"

    def __init__(self, api_key: str, api_base_url: Optional[str] = None, config: dict = None):
        super().__init__(api_key=api_key, api_base_url=api_base_url, config=config or {})
        self.base_url = (api_base_url or self.DEFAULT_BASE).rstrip("/")
        self.timezone_id = (config or {}).get("timezone_id", 67)  # 90 = UTC

    def _headers(self) -> dict:
        return {
            "X-Eflow-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _col(self, columns: list, col_type: str) -> str:
        """Extract a value from an Everflow columns array by column_type."""
        for c in columns:
            if c.get("column_type") == col_type:
                return c.get("id", "")
        return ""

    def _col_label(self, columns: list, col_type: str) -> str:
        for c in columns:
            if c.get("column_type") == col_type:
                return c.get("label", "")
        return ""

    def _ts_to_date(self, ts) -> Optional[str]:
        """Convert a Unix timestamp (or date string) to YYYY-MM-DD."""
        if not ts:
            return None
        try:
            return datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            return str(ts) if ts else None

    async def get_campaigns(self) -> list[dict]:
        """Return all runnable (approved) offers for this affiliate."""
        page = 1
        page_size = 500
        all_offers = []
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                resp = await client.get(
                    f"{self.base_url}/affiliates/offersrunnable",
                    headers=self._headers(),
                    params={"page": page, "page_size": page_size},
                )
                resp.raise_for_status()
                data = resp.json()
                offers = data.get("offers", [])
                all_offers.extend(offers)
                paging = data.get("paging", {})
                total = paging.get("total_count", 0)
                if len(all_offers) >= total or not offers:
                    break
                page += 1

        return [
            {
                "id": str(o.get("network_offer_id", "")),
                "name": o.get("name", ""),
                "status": o.get("offer_status", "active"),
            }
            for o in all_offers
            if o.get("network_offer_id")
        ]

    async def get_stats(self, start_date: date, end_date: date, campaign_id: Optional[str] = None) -> list[dict]:
        """Pull daily stats per offer, including sub1 breakdown."""
        payload = {
            "from": str(start_date),
            "to": str(end_date),
            "timezone_id": self.timezone_id,
            "currency_id": "USD",
            "columns": [
                {"column": "offer"},
                {"column": "sub1"},
                {"column": "date"},
            ],
            "query": {"filters": []},
        }
        if campaign_id:
            payload["query"]["filters"].append({
                "filter_id_value": campaign_id,
                "resource_type": "offer",
            })

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/affiliates/reporting/entity/table",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        rows = data.get("table", [])
        results = []
        for row in rows:
            cols = row.get("columns", [])
            rep = row.get("reporting", {})
            offer_id = self._col(cols, "offer")
            offer_name = self._col_label(cols, "offer")
            date_ts = self._col(cols, "date")
            sub1 = self._col(cols, "sub1") or None

            results.append({
                "campaign_id": str(offer_id),
                "campaign_name": offer_name,
                "date": self._ts_to_date(date_ts),
                "clicks": int(rep.get("total_click", 0) or 0),
                "conversions": int(rep.get("cv", 0) or 0),
                "revenue": float(rep.get("revenue", 0) or 0),
                "payout": float(rep.get("revenue", 0) or 0),  # affiliate sees revenue as payout
                "sub_id": sub1 if sub1 and sub1 != "0" else None,
                "raw": rep,
            })
        return results

    async def get_sub_id_stats(self, sub_id: str, start_date: date, end_date: date) -> list[dict]:
        """Pull stats filtered to a specific sub1 value."""
        payload = {
            "from": str(start_date),
            "to": str(end_date),
            "timezone_id": self.timezone_id,
            "currency_id": "USD",
            "columns": [
                {"column": "offer"},
                {"column": "sub1"},
                {"column": "date"},
            ],
            "query": {
                "filters": [
                    {"filter_id_value": sub_id, "resource_type": "sub1"}
                ]
            },
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/affiliates/reporting/entity/table",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        rows = data.get("table", [])
        results = []
        for row in rows:
            cols = row.get("columns", [])
            rep = row.get("reporting", {})
            offer_id = self._col(cols, "offer")
            offer_name = self._col_label(cols, "offer")
            date_ts = self._col(cols, "date")

            results.append({
                "campaign_id": str(offer_id),
                "campaign_name": offer_name,
                "date": self._ts_to_date(date_ts),
                "clicks": int(rep.get("total_click", 0) or 0),
                "conversions": int(rep.get("cv", 0) or 0),
                "revenue": float(rep.get("revenue", 0) or 0),
                "payout": float(rep.get("revenue", 0) or 0),
                "sub_id": sub_id,
                "raw": rep,
            })
        return results
