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

    async def get_joe_sub_ids(self, start_date, end_date) -> list[dict]:
        """
        Enumerate all of Joe's unique Sub IDs (sub1 for Everflow) seen in the period.
        """
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
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/affiliates/reporting/entity/table",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for row in data.get("table", []):
            cols = row.get("columns", [])
            rep = row.get("reporting", {})
            sub1 = self._col(cols, "sub1") or None
            if not sub1 or sub1 == "0":
                continue
            results.append({
                "sub_id_value": sub1,
                "campaign_name": self._col_label(cols, "offer"),
                "date": self._ts_to_date(self._col(cols, "date")),
                "clicks": int(rep.get("total_click", 0) or 0),
                "conversions": int(rep.get("cv", 0) or 0),
                "revenue": float(rep.get("revenue", 0) or 0),
            })
        return results


    async def get_conversions(self, start_date, end_date) -> list[dict]:
        """Pull conversion-level rows with actual conversion timestamps."""
        payload = {
            "from": f"{start_date} 00:00:00",
            "to": f"{end_date} 23:59:59",
            "timezone_id": self.timezone_id,
            "currency_id": "USD",
            "show_conversions": True,
            "show_events": False,
            "query": {"filters": []},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/affiliates/reporting/conversions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        raw_rows = data.get("conversions") or data.get("table") or data.get("data") or []
        if isinstance(raw_rows, dict):
            raw_rows = raw_rows.get("conversions") or raw_rows.get("entries") or list(raw_rows.values())

        results = []
        for row in raw_rows:
            conv = row.get("conversion", row) if isinstance(row, dict) else {}
            conv_id = (
                conv.get("conversion_id") or conv.get("network_conversion_id") or conv.get("id")
                or conv.get("transaction_id") or conv.get("event_id")
            )
            ts = conv.get("conversion_unix_timestamp") or conv.get("unix_timestamp") or conv.get("conversion_time")
            if not conv_id or not ts:
                continue
            offer = conv.get("offer") or conv.get("network_offer") or {}
            offer_id = conv.get("network_offer_id") or conv.get("offer_id") or offer.get("network_offer_id") or offer.get("id")
            offer_name = conv.get("offer_name") or offer.get("name") or ""
            sub1 = conv.get("sub1") or conv.get("sub_id1") or conv.get("source_id") or None
            revenue = conv.get("revenue") or conv.get("payout") or conv.get("sale_amount") or 0
            results.append({
                "network_conversion_id": str(conv_id),
                "conversion_at": ts,
                "campaign_id": str(offer_id or ""),
                "campaign_name": offer_name,
                "sub_id": sub1 if sub1 and sub1 != "0" else None,
                "sub_id1": sub1 if sub1 and sub1 != "0" else None,
                "revenue": float(revenue or 0),
                "status": conv.get("conversion_status") or conv.get("status"),
                "raw": conv,
            })
        return results
