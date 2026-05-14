from playwright.async_api import Page
from .base import ATSAdapter
from ..stealth import human_type, human_click, gaussian_wait

class GreenhouseAdapter(ATSAdapter):
    async def is_matching(self) -> bool:
        return "boards.greenhouse.io" in self.page.url

    async def fill_application(self, data: dict) -> str:
        await human_type(self.page, "input#first_name", data.get("first_name", ""))
        await gaussian_wait(0.5, 0.1)
        await human_type(self.page, "input#last_name", data.get("last_name", ""))
        await gaussian_wait(0.5, 0.1)
        await human_type(self.page, "input#email", data.get("email", ""))
        await gaussian_wait(0.8, 0.2)
        
        if data.get("cv_path"):
            try:
                await self.page.set_input_files("input[type='file']", data["cv_path"])
                await gaussian_wait(1.5, 0.3)
            except Exception:
                pass

        if data.get("cover_letter_path"):
            file_inputs = await self.page.query_selector_all("input[type='file']")
            if len(file_inputs) > 1:
                try:
                    await file_inputs[1].set_input_files(data["cover_letter_path"])
                except Exception:
                    pass

        if data.get("approved", False):
            snapshot_path = await self.take_snapshot(data.get("application_id", "unknown"))
            await human_click(self.page, "input[type='submit'], button[type='submit']")
            return snapshot_path
        
        return ""
