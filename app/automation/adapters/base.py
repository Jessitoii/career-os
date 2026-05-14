from abc import ABC, abstractmethod
import logging
import asyncio
from typing import Dict, Any
from playwright.async_api import Page, TimeoutError
import time

logger = logging.getLogger(__name__)

class ATSAdapter(ABC):
    def __init__(self, page: Page):
        self.page = page
        self.platform_id = "unknown" # Should be overridden by subclasses

    @abstractmethod
    async def is_matching(self) -> bool:
        """Determine if this page belongs to this ATS."""
        pass

    async def check_for_blockers(self) -> bool:
        """Detect CAPTCHAs, Cloudflare checks, or unexpected identity verification loops."""
        blocker_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "div.cf-browser-verification",
            "text='Verify you are human'",
            "text='Access Denied'"
        ]
        
        for selector in blocker_selectors:
            try:
                # Fast check without waiting
                count = await self.page.locator(selector).count()
                if count > 0:
                    logger.warning(f"BLOCKED: Detected anti-bot mechanism: {selector}")
                    return True
            except Exception:
                pass
        return False

    async def safe_fill(self, selectors: list[str] | str, value: str, field_name: str = None, human_delay: bool = True):
        """Fill a field safely using a cascading list of fuzzy selectors."""
        from app.core.db import SessionLocal
        from app.models.selectors import SelectorIntelligence
        from datetime import datetime
        
        if await self.check_for_blockers():
            raise Exception("requires_human: Bot blocked during safe_fill.")
            
        if isinstance(selectors, str):
            selectors = [selectors]
            
        # Try to prepend the historically best selector if we have a field_name
        db = SessionLocal()
        best_selector = None
        try:
            if field_name:
                intel = db.query(SelectorIntelligence).filter(
                    SelectorIntelligence.platform == self.platform_id,
                    SelectorIntelligence.field_name == field_name
                ).first()
                if intel and intel.successful_selector not in selectors:
                    selectors.insert(0, intel.successful_selector)
        finally:
            db.close()
            
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                # Use a fast timeout for fuzzy finding
                await locator.wait_for(state="visible", timeout=2000)
                
                if human_delay:
                    for char in value:
                        await locator.type(char, delay=50) # Simulate keystrokes
                else:
                    await locator.fill(value)
                    
                # We succeeded. Persist intelligence.
                if field_name:
                    db = SessionLocal()
                    try:
                        intel = db.query(SelectorIntelligence).filter(
                            SelectorIntelligence.platform == self.platform_id,
                            SelectorIntelligence.field_name == field_name
                        ).first()
                        if not intel:
                            intel = SelectorIntelligence(
                                platform=self.platform_id,
                                field_name=field_name,
                                successful_selector=selector
                            )
                            db.add(intel)
                        else:
                            if intel.successful_selector != selector:
                                intel.successful_selector = selector
                                intel.success_count = 1
                            else:
                                intel.success_count += 1
                            intel.last_success_at = datetime.utcnow()
                        db.commit()
                    finally:
                        db.close()
                return # Exit on success
            except TimeoutError:
                logger.debug(f"Selector '{selector}' failed. Trying next...")
                continue
                
        # If all selectors fail, dump a screenshot
        err_shot = f"./storage/traces/error_selector_{self.platform_id}_{field_name}.png"
        await self.page.screenshot(path=err_shot)
        raise TimeoutError(f"All fuzzy selectors failed for field '{field_name}'. Screenshot saved: {err_shot}")

    async def safe_submit(self, submit_selector: str, is_dry_run: bool = True) -> str:
        """
        Executes the final submit click if not in dry_run mode.
        Returns the path to the proof snapshot.
        """
        if await self.check_for_blockers():
            raise Exception("requires_human: Bot blocked right before submission.")

        submit_btn = self.page.locator(submit_selector)
        await submit_btn.wait_for(state="visible", timeout=5000)
        
        # Take a snapshot right before clicking
        pre_submit_shot = f"./storage/traces/pre_submit_{id(self)}.png"
        await self.page.screenshot(path=pre_submit_shot)

        if is_dry_run:
            logger.info("DRY_RUN: Stopping before final submit click.")
            return pre_submit_shot
        
        logger.info("LIVE RUN: Executing final application submit.")
        await submit_btn.click()
        
        # Wait for success confirmation page
        await self.page.wait_for_load_state("networkidle")
        
        post_submit_shot = f"./storage/traces/post_submit_{id(self)}.png"
        await self.page.screenshot(path=post_submit_shot)
        return post_submit_shot

    @abstractmethod
    async def fill_application(self, data: Dict[str, Any]) -> str:
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
