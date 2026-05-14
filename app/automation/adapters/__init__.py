from .base import ATSAdapter
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .workday import WorkdayAdapter

ADAPTER_REGISTRY = [
    GreenhouseAdapter,
    LeverAdapter,
    WorkdayAdapter,
]

async def detect_adapter(page) -> ATSAdapter | None:
    for AdapterClass in ADAPTER_REGISTRY:
        adapter = AdapterClass(page)
        if await adapter.is_matching():
            return adapter
    return None
