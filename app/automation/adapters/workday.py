from playwright.async_api import Page
from .base import ATSAdapter
from ..stealth import human_type, human_click, gaussian_wait

class WorkdayAdapter(ATSAdapter):
    async def is_matching(self) -> bool:
        return ".myworkdayjobs.com" in self.page.url

    async def fill_application(self, data: dict) -> str:
        # Workday uses shadow DOM
        try:
            await self.page.locator("pierce/[data-automation-id='legalNameSection_firstName']").fill(data.get("first_name", ""))
            await gaussian_wait(0.8, 0.2)
            await self.page.locator("pierce/[data-automation-id='legalNameSection_lastName']").fill(data.get("last_name", ""))
            
            await self.page.wait_for_selector("pierce/[data-automation-id='email']", state="attached", timeout=15000)
            await self.page.locator("pierce/[data-automation-id='email']").fill(data.get("email", ""))
            await gaussian_wait(0.8, 0.2)
        except Exception:
            pass

        if data.get("approved", False):
            snapshot_path = await self.take_snapshot(data.get("application_id", "unknown"))
            try:
                await self.page.locator("pierce/[data-automation-id='bottom-navigation-next-button']").click()
            except Exception:
                pass
            return snapshot_path
            
        return ""
