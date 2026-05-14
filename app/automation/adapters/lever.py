from playwright.async_api import Page
from .base import ATSAdapter
from ..stealth import human_type, human_click, gaussian_wait

class LeverAdapter(ATSAdapter):
    async def is_matching(self) -> bool:
        return "jobs.lever.co" in self.page.url

    async def fill_application(self, data: dict) -> str:
        await human_type(self.page, "input[name='name']", f"{data.get('first_name', '')} {data.get('last_name', '')}")
        await gaussian_wait(0.5, 0.1)
        await human_type(self.page, "input[name='email']", data.get("email", ""))
        await gaussian_wait(0.8, 0.2)
        
        if data.get("cv_path"):
            try:
                await self.page.set_input_files("input[type='file']", data["cv_path"])
                await gaussian_wait(1.5, 0.3)
            except Exception:
                pass

        if data.get("approved", False):
            snapshot_path = await self.take_snapshot(data.get("application_id", "unknown"))
            await human_click(self.page, "button.postings-btn[type='submit']")
            return snapshot_path
        
        return ""
