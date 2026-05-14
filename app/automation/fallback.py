import logging
from playwright.async_api import Page
from .stealth import human_type
from app.intelligence.llm_client import call_with_fallback
from app.intelligence.prompts import DOM_VISION_PROMPT, DOMVisionOutput

logger = logging.getLogger(__name__)

FIELD_HEURISTICS = {
    "first_name": ["input[name*='first']", "input[id*='first']", "input[placeholder*='First']"],
    "last_name":  ["input[name*='last']",  "input[id*='last']",  "input[placeholder*='Last']"],
    "email":      ["input[type='email']",  "input[name*='email']"],
    "cv":         ["input[type='file']"],
}

async def heuristic_fill(page: Page, data: dict) -> bool:
    """Attempt dictionary-based heuristic field matching."""
    success_count = 0
    for field, selectors in FIELD_HEURISTICS.items():
        for selector in selectors:
            try:
                el = await page.query_selector(selector)
                if el:
                    await human_type(page, selector, data.get(field, ""))
                    success_count += 1
                    break
            except Exception:
                continue
                
    return success_count > 0

async def llm_vision_fallback(page: Page, field_label: str) -> str | None:
    """Use GPT-4o / Gemini to find the CSS selector visually."""
    # NOTE: Vision capability simulated via DOM fallback
    try:
        # In a real setup, we'd pass the screenshot_b64 and ax_tree
        # screenshot_b64 = await page.screenshot(type="png", full_page=False)
        ax_tree = await page.accessibility.snapshot()
        
        prompt = DOM_VISION_PROMPT.format(field_label=field_label)
        
        result = await call_with_fallback(
            task="dom_vision_fallback",
            system="You are a frontend expert. Return only the CSS selector string.",
            user=f"Context: {str(ax_tree)[:2000]}\n{prompt}",
            schema_model=DOMVisionOutput
        )
        
        return result.selector
    except Exception as e:
        logger.error(f"Vision fallback failed: {e}")
        return None

async def hitl_fallback(page: Page, application_id: str, field_label: str):
    """
    If LLM fails, we trigger HITL in telegram. 
    This would be coordinated by the state machine and telegram bot.
    """
    logger.info(f"Triggering HITL fallback for {application_id} - {field_label}")
    path = f"/tmp/{application_id}_hitl.png"
    await page.screenshot(path=path)
    return path
