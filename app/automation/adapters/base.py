from abc import ABC, abstractmethod
from playwright.async_api import Page
import time

class ATSAdapter(ABC):
    def __init__(self, page: Page):
        self.page = page

    @abstractmethod
    async def is_matching(self) -> bool:
        """Determine if this page belongs to this ATS."""
        pass

    @abstractmethod
    async def fill_application(self, data: dict) -> None:
        """Form filling logic — DO NOT submit unless status is 'approved'."""
        pass

    async def take_snapshot(self, application_id: str) -> str:
        """Take a screenshot for before and after submit."""
        path = f"/tmp/{application_id}_{int(time.time())}.png"
        try:
            await self.page.screenshot(path=path, full_page=True)
            return path
        except Exception:
            return ""
