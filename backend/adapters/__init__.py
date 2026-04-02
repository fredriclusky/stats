from backend.adapters.base import BaseAdapter
from backend.adapters.hasoffers import HasOffersAdapter
from backend.adapters.everflow import EverflowAdapter

ADAPTER_REGISTRY = {
    "hasoffers": HasOffersAdapter,
    "everflow": EverflowAdapter,
}


def get_adapter(
    network_type: str,
    api_key: str,
    api_base_url: str = None,
    network_id_value: str = None,
    config: dict = None
) -> BaseAdapter:
    cls = ADAPTER_REGISTRY.get(network_type)
    if not cls:
        raise ValueError(f"Unknown network type: {network_type}. Supported: {list(ADAPTER_REGISTRY.keys())}")
    # Merge network_id_value into config so adapters can access it consistently
    merged_config = dict(config or {})
    if network_id_value:
        merged_config["network_id"] = network_id_value
    return cls(api_key=api_key, api_base_url=api_base_url, config=merged_config)
