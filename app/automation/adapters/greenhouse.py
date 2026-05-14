import logging
from typing import Dict, Any
from .base import ATSAdapter

logger = logging.getLogger(__name__)

class GreenhouseAdapter(ATSAdapter):
    
    @classmethod
    async def is_match(cls, page) -> bool:
        """Check if URL or DOM matches Greenhouse."""
        return "greenhouse.io" in page.url or await page.locator("div#header").count() > 0

    async def fill_application(self, data: Dict[str, Any]) -> str:
        """
        Fills out a standard Greenhouse job application.
        Returns the path to the confirmation screenshot.
        """
        logger.info(f"GreenhouseAdapter starting for App ID: {data.get('application_id')}")

        # Basic Info
        await self.safe_fill("input[name='first_name']", data.get("first_name", ""))
        await self.safe_fill("input[name='last_name']", data.get("last_name", ""))
        await self.safe_fill("input[name='email']", data.get("email", ""))
        
        # Phone if available
        if "phone" in data:
            await self.safe_fill("input[name='phone']", data["phone"])

        # Resume Upload
        cv_path = data.get("cv_path")
        if cv_path:
            logger.info("Uploading resume...")
            file_input = self.page.locator("input[type='file'][name='resume']")
            if await file_input.count() > 0:
                await file_input.set_input_files(cv_path)

        # Standard questions (authorization, visa)
        auth_radios = self.page.locator("text='Are you legally authorized'")
        if await auth_radios.count() > 0:
            await self.page.locator("input[type='radio'][value='Yes']").first.click()

        visa_radios = self.page.locator("text='require sponsorship'")
        if await visa_radios.count() > 0:
            await self.page.locator("input[type='radio'][value='No']").last.click()

        # Submit
        is_dry_run = not data.get("approved", False)
        return await self.safe_submit("button#submit_app, input#submit_app", is_dry_run=is_dry_run)
