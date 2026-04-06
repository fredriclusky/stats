from datetime import date
from typing import Optional
import httpx
from backend.adapters.base import BaseAdapter


class HasOffersAdapter(BaseAdapter):
    """
    HasOffers (TUNE) Affiliate API adapter.

    Sub ID convention (affiliate mode):
      - affiliate_info1  →  sub_id1  — campaign identifier shared across accounts
      - affiliate_info2  →  sub_id   — Joe's Sub ID (queried live for outbound revenue)

    NOTE: HasOffers does not correctly aggregate payout/clicks when grouping by
    multiple affiliate_info fields simultaneously. get_stats() therefore groups
    by sub1 only to keep totals accurate. Joe's sub2 revenue is fetched live
    via get_sub_id_stats() which filters by affiliate_info2.
    """

    DEFAULT_BASE = "https://api.hasoffers.com/Apiv3/json"
    API_PATH = "/Apiv3/json"

    def __init__(self, api_key: str, api_base_url: Optional[str] = None, config: dict = None):
        super().__init__(api_key=api_key, api_base_url=api_base_url, config=config or {})
        cfg = config or {}
        self.network_id = cfg.get("network_id", "")
        self.access_mode = cfg.get("access_mode", "affiliate")
        self.base_url = self._normalize_url(api_base_url)
        if not self.network_id:
            raise ValueError(
                "HasOffers requires a Network ID. "
                "Enter the network subdomain (e.g. 'neptuneads') in the Network ID field."
            )

    def _normalize_url(self, url: Optional[str]) -> str:
        if not url:
            return self.DEFAULT_BASE
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url
        import re as _re
        if _re.search(r'[a-z0-9\-]+\.hasoffers\.com$', url) and 'api.hasoffers.com' not in url:
            return self.DEFAULT_BASE
        if not url.endswith("/Apiv3/json"):
            url = url + self.API_PATH
        return url

    def _auth_params(self) -> dict:
        if self.access_mode == "network":
            return {"NetworkId": self.network_id, "NetworkToken": self.api_key}
        return {"NetworkId": self.network_id, "api_key": self.api_key}

    async def _request(self, target: str, method: str, params: dict = None) -> dict:
        all_params = {
            **self._auth_params(),
            "Target": target,
            "Method": method,
            **(params or {})
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.base_url, params=all_params)
            resp.raise_for_status()
            text = resp.text.strip()
            if not text:
                raise Exception(
                    f"HasOffers returned an empty response. "
                    f"Check that the API URL is correct (used: {self.base_url}) "
                    f"and that Network ID '{self.network_id}' is valid."
                )
            data = resp.json()
            response_data = data.get("response", data)
            if response_data.get("status") != 1:
                errors = response_data.get("errors", [])
                msg = (errors[0].get("publicMessage", str(errors)) if errors
                       else response_data.get("errorMessage", "Unknown error"))
                raise Exception(f"HasOffers API error: {msg}")
            return response_data.get("data", {})

    async def _request_all_pages(self, target: str, method: str, params: dict = None) -> list:
        base_params = dict(params or {})
        page = 1
        all_rows = []
        while True:
            paged = {**base_params, "page": str(page), "limit": "500"}
            data = await self._request(target, method, paged)
            if isinstance(data, list):
                all_rows.extend(data)
                break
            if isinstance(data, dict):
                inner = data.get("data", data)
                if isinstance(inner, list):
                    all_rows.extend(inner)
                elif isinstance(inner, dict):
                    all_rows.extend(inner.values())
                total_pages = int(data.get("pageCount", 1))
            else:
                break
            if page >= total_pages:
                break
            page += 1
        return all_rows

    async def get_campaigns(self) -> list[dict]:
        if self.access_mode == "network":
            data = await self._request(
                "Offer", "findAll",
                {"filters[status]": "active", "fields[]": ["id", "name", "status"], "limit": "500"}
            )
            offers = list(data.values()) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        else:
            offers = await self._request_all_pages(
                "Affiliate_Offer", "findMyApprovedOffers",
                {"fields[]": ["id", "name", "status"]}
            )
        results = []
        for o in offers:
            offer = o.get("Offer", o)
            results.append({
                "id": str(offer.get("id", "")),
                "name": offer.get("name", ""),
                "status": offer.get("status", ""),
            })
        return [r for r in results if r["id"]]

    async def get_stats(self, start_date: date, end_date: date, campaign_id: Optional[str] = None) -> list[dict]:
        """
        Pull daily stats grouped by offer + affiliate_info1 (Sub ID 1 = campaign identifier).

        Sub ID 1 (affiliate_info1) is stored as sub_id1 — the campaign label shared across accounts.
        Sub ID 2 (affiliate_info2 = Joe's sub ID) is NOT grouped here because HasOffers drops
        clicks/payout attribution when grouping by multiple affiliate_info fields simultaneously.
        Joe's revenue is instead fetched live via get_sub_id_stats().
        """
        if self.access_mode == "network":
            target, info1_field = "Report", "Stat.sub1"
        else:
            target, info1_field = "Affiliate_Report", "Stat.affiliate_info1"

        params = {
            "fields[]": [
                "Stat.date",
                "Stat.offer_id",
                "Offer.name",
                "Stat.clicks",
                "Stat.conversions",
                "Stat.payout",
                info1_field,
            ],
            "groups[]": ["Stat.date", "Stat.offer_id", info1_field],
            "filters[Stat.date][conditional]": "BETWEEN",
            "filters[Stat.date][values][]": [str(start_date), str(end_date)],
            "totals": "1",
        }
        if campaign_id:
            params["filters[Stat.offer_id][conditional]"] = "EQUAL_TO"
            params["filters[Stat.offer_id][values][]"] = campaign_id

        rows = await self._request_all_pages(target, "getStats", params)
        results = []
        for row in rows:
            stat = row.get("Stat", row)
            offer = row.get("Offer", {})
            sub1 = stat.get("affiliate_info1") or stat.get("sub1") or None
            results.append({
                "campaign_id": str(stat.get("offer_id", "")),
                "campaign_name": offer.get("name", ""),
                "date": stat.get("date"),
                "clicks": int(stat.get("clicks", 0) or 0),
                "conversions": int(stat.get("conversions", 0) or 0),
                "revenue": float(stat.get("payout", 0) or 0),
                "payout": float(stat.get("payout", 0) or 0),
                "sub_id": None,      # sub_id (Joe's sub2) not stored in main sync
                "sub_id1": sub1,     # sub_id1 = campaign identifier (affiliate_info1)
                "raw": stat,
            })
        return results

    async def get_sub_id_stats(self, sub_id: str, start_date: date, end_date: date) -> list[dict]:
        """
        Pull revenue for a specific Joe's Sub ID (affiliate_info2).
        Groups by date+offer+sub1 for context, filtered to this sub2 value.
        """
        if self.access_mode == "network":
            target = "Report"
            info1_field = "Stat.sub1"
            info2_field = "Stat.sub2"
            filter_key_cond = "filters[Stat.sub2][conditional]"
            filter_key_val = "filters[Stat.sub2][values][]"
        else:
            target = "Affiliate_Report"
            info1_field = "Stat.affiliate_info1"
            info2_field = "Stat.affiliate_info2"
            filter_key_cond = "filters[Stat.affiliate_info2][conditional]"
            filter_key_val = "filters[Stat.affiliate_info2][values][]"

        params = {
            "fields[]": [
                "Stat.date",
                "Stat.offer_id",
                "Offer.name",
                "Stat.clicks",
                "Stat.conversions",
                "Stat.payout",
                info1_field,
                info2_field,
            ],
            "groups[]": ["Stat.date", "Stat.offer_id", info1_field],
            "filters[Stat.date][conditional]": "BETWEEN",
            "filters[Stat.date][values][]": [str(start_date), str(end_date)],
            filter_key_cond: "EQUAL_TO",
            filter_key_val: sub_id,
        }
        rows = await self._request_all_pages(target, "getStats", params)
        results = []
        for row in rows:
            stat = row.get("Stat", row)
            offer = row.get("Offer", {})
            sub1 = stat.get("affiliate_info1") or stat.get("sub1") or None
            results.append({
                "campaign_id": str(stat.get("offer_id", "")),
                "campaign_name": offer.get("name", ""),
                "date": stat.get("date"),
                "clicks": int(stat.get("clicks", 0) or 0),
                "conversions": int(stat.get("conversions", 0) or 0),
                "revenue": float(stat.get("payout", 0) or 0),
                "payout": float(stat.get("payout", 0) or 0),
                "sub_id": sub_id,
                "sub_id1": sub1,
                "raw": stat,
            })
        return results

    async def get_joe_sub_ids(self, start_date, end_date) -> list[dict]:
        """
        Enumerate all of Joe's unique Sub IDs (affiliate_info2 / slot 2) seen in the period.
        Groups by date + offer + affiliate_info2 only — no accuracy issue since info1 is excluded.
        Skips rows where affiliate_info2 is empty.
        """
        if self.access_mode == "network":
            target, info2_field = "Report", "Stat.sub2"
        else:
            target, info2_field = "Affiliate_Report", "Stat.affiliate_info2"

        params = {
            "fields[]": [
                "Stat.date", "Stat.offer_id", "Offer.name",
                "Stat.clicks", "Stat.conversions", "Stat.payout", info2_field,
            ],
            "groups[]": ["Stat.date", "Stat.offer_id", info2_field],
            "filters[Stat.date][conditional]": "BETWEEN",
            "filters[Stat.date][values][]": [str(start_date), str(end_date)],
            "totals": "1",
        }
        rows = await self._request_all_pages(target, "getStats", params)
        results = []
        for row in rows:
            stat = row.get("Stat", row)
            offer = row.get("Offer", {})
            sub2 = stat.get("affiliate_info2") or stat.get("sub2") or None
            if not sub2:
                continue
            results.append({
                "sub_id_value": sub2,
                "campaign_name": offer.get("name", ""),
                "date": stat.get("date"),
                "clicks": int(stat.get("clicks", 0) or 0),
                "conversions": int(stat.get("conversions", 0) or 0),
                "revenue": float(stat.get("payout", 0) or 0),
            })
        return results
