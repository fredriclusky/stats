from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class BaseAdapter(ABC):
    """
    Base interface all affiliate network adapters must implement.
    To add a new network: create a new file in adapters/, subclass BaseAdapter,
    and register it in adapters/__init__.py ADAPTER_REGISTRY.
    """

    def __init__(self, api_key: str, api_base_url: Optional[str] = None, config: dict = None):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.config = config or {}

    @abstractmethod
    async def get_campaigns(self) -> list[dict]:
        """
        Return list of campaigns from the network.
        Each dict: { "id": str, "name": str, "status": str, ...extra }
        """
        pass

    @abstractmethod
    async def get_stats(self, start_date: date, end_date: date, campaign_id: Optional[str] = None) -> list[dict]:
        """
        Return stats for date range.
        Each dict: { "campaign_id": str, "date": date, "clicks": int, "conversions": int, "revenue": float, "sub_id": str|None, ...extra }
        """
        pass

    @abstractmethod
    async def get_sub_id_stats(self, sub_id: str, start_date: date, end_date: date) -> list[dict]:
        """
        Return stats broken down by sub_id.
        """
        pass

    async def test_connection(self) -> bool:
        """Test that the API credentials are valid."""
        try:
            campaigns = await self.get_campaigns()
            return True
        except Exception:
            return False
