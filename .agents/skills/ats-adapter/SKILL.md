---
name: ats-adapter
description: Use when writing, modifying, or debugging browser automation code for a specific job application portal — Greenhouse, Lever, Workday, or an unknown custom ATS. Triggers on: "ATS adapter", "new adapter", "write new adapter", "Workday form", "Greenhouse selector", "Lever integration", "unknown portal", "custom ATS", "LLM vision fallback", "DOM selector not found", "form automation", "apply engine", "portal scraper", "shadow DOM", "form is being filled".
---

# ATS Adapter Skill

## Use this skill when
- Writing an adapter for a new ATS platform (Greenhouse, Lever, Workday, Ashby, etc.)
- Debugging a selector or form filling error in an existing adapter
- Implementing the LLM Vision / DOM fallback mechanism for an unknown portal
- Hooking up the HITL Telegram screenshot flow for an unknown UI
- Registering a new platform in the `AdapterRegistry`

## Do not use this skill when
- Configuring general Playwright stealth settings → use the `stealth-browser` skill
- Modifying the state machine or session lifecycle → use the `session-lifecycle` skill
- Updating only rate limit values → use the `db-schema` skill

---

## Architecture: Adapter Pattern

All adapters are derived from the `ATSAdapter` abstract base class.
Every adapter implements two methods:
- `is_matching(page) -> bool`: Platform detection via URL/DOM analysis
- `fill_application(data: dict)`: Platform-specific form filling logic

### Source Files
```
app/
├── automation/
│   ├── adapters/
│   │   ├── __init__.py          ← AdapterRegistry is here
│   │   ├── base.py              ← ATSAdapter ABC
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── workday.py
│   │   └── <new_platform>.py
│   ├── stealth.py               ← stealth helpers
│   └── fallback.py              ← LLM vision / HITL fallback
```

### Base Class (app/automation/adapters/base.py)
```python
from abc import ABC, abstractmethod
from playwright.async_api import Page
from typing import Optional

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
        path = f"/tmp/snapshots/{application_id}_{int(time.time())}.png"
        await self.page.screenshot(path=path, full_page=True)
        return path
```

### AdapterRegistry (app/automation/adapters/__init__.py)
```python
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .workday import WorkdayAdapter

ADAPTER_REGISTRY = [
    GreenhouseAdapter,
    LeverAdapter,
    WorkdayAdapter,
    # Add new adapters here
]

async def detect_adapter(page) -> ATSAdapter | None:
    for AdapterClass in ADAPTER_REGISTRY:
        adapter = AdapterClass(page)
        if await adapter.is_matching():
            return adapter
    return None  # Unknown portal → fallback mechanism kicks in
```

---

## Known Adapters

| Adapter | Detection Signal | Special Notes |
|---|---|---|
| `GreenhouseAdapter` | `boards.greenhouse.io` in URL | Flat DOM, standard selectors |
| `LeverAdapter` | `jobs.lever.co` in URL | Similar to Greenhouse |
| `WorkdayAdapter` | `.myworkdayjobs.com` in URL | Shadow DOM, `pierce/` selector required |

### Greenhouse Adapter (app/automation/adapters/greenhouse.py)
```python
from playwright.async_api import Page
from .base import ATSAdapter
from ..stealth import human_type, human_click, gaussian_wait

class GreenhouseAdapter(ATSAdapter):
    async def is_matching(self) -> bool:
        return "boards.greenhouse.io" in self.page.url

    async def fill_application(self, data: dict) -> None:
        await human_type(self.page, "input#first_name", data["first_name"])
        await gaussian_wait(0.5, 0.1)
        await human_type(self.page, "input#last_name", data["last_name"])
        await gaussian_wait(0.5, 0.1)
        await human_type(self.page, "input#email", data["email"])
        await gaussian_wait(0.8, 0.2)
        await self.page.set_input_files("input[type='file']", data["cv_path"])
        await gaussian_wait(1.5, 0.3)

        # If there is a cover letter
        if data.get("cover_letter_path"):
            # In Greenhouse, the second file input is usually the cover letter
            file_inputs = await self.page.query_selector_all("input[type='file']")
            if len(file_inputs) > 1:
                await file_inputs[1].set_input_files(data["cover_letter_path"])

        # SAFETY: only submit if status is 'approved'
        if data.get("approved", False):
            snapshot_path = await self.take_snapshot(data["application_id"])
            await human_click(self.page, "input[type='submit'], button[type='submit']")
            return snapshot_path
```

### Workday Adapter — Shadow DOM (app/automation/adapters/workday.py)
```python
class WorkdayAdapter(ATSAdapter):
    async def is_matching(self) -> bool:
        return ".myworkdayjobs.com" in self.page.url

    async def fill_application(self, data: dict) -> None:
        # Workday shadow DOM: selector with pierce/ prefix
        await self.page.locator(
            "pierce/[data-automation-id='legalNameSection_firstName']"
        ).fill(data["first_name"])
        await gaussian_wait(0.8, 0.2)

        await self.page.locator(
            "pierce/[data-automation-id='legalNameSection_lastName']"
        ).fill(data["last_name"])

        # Workday dynamic loading — must wait for the form element at each step
        await self.page.wait_for_selector(
            "pierce/[data-automation-id='email']",
            state="attached",
            timeout=15000
        )
        await self.page.locator(
            "pierce/[data-automation-id='email']"
        ).fill(data["email"])
```

---

## Unknown Portal Fallback Hierarchy

When `detect_adapter()` returns `None`, the sequence is:

### Layer 1: Heuristic Mapping
```python
FIELD_HEURISTICS = {
    "first_name": ["input[name*='first']", "input[id*='first']", "input[placeholder*='First']"],
    "last_name":  ["input[name*='last']",  "input[id*='last']",  "input[placeholder*='Last']"],
    "email":      ["input[type='email']",  "input[name*='email']"],
    "cv":         ["input[type='file']"],
}

async def heuristic_fill(page, data: dict) -> bool:
    for field, selectors in FIELD_HEURISTICS.items():
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                await human_type(page, selector, data.get(field, ""))
                break
        else:
            return False  # This field was not found → Move to Layer 2
    return True
```

### Layer 2: LLM Vision / DOM Fallback
```python
async def llm_vision_fallback(page: Page, field_label: str) -> str | None:
    """Find the CSS selector from the screenshot with GPT-4o or Gemini."""
    screenshot_b64 = await page.screenshot(type="png", full_page=False)
    ax_tree = await page.accessibility.snapshot()

    prompt = f"""
    Find the CSS selector for the '{field_label}' field on this form page.
    ONLY return the selector string, do not write anything else.
    Example output: input[name='salary_expectation']
    """
    # call_with_fallback("dom_vision_fallback", {screenshot, ax_tree, prompt})
    # Verify and use the returned selector
```

### Layer 3: HITL Telegram
```python
async def hitl_fallback(page: Page, application_id: str, field_label: str):
    """If LLM failed, ask the user, save the response to memory."""
    screenshot_path = await take_snapshot(application_id)
    await send_telegram_photo(
        screenshot_path,
        caption=f"⚠️ Unknown field: *{field_label}*\nPlease send the CSS selector."
    )
    # Save the user response to interaction_logs (learned behavior)
    # This selector is used when the same site is seen again
```

---

## Steps to Add a New Adapter

1. Create `app/automation/adapters/<platform>.py`, derive from `ATSAdapter`
2. `is_matching()`: Perform URL pattern check (look at the URL before the DOM — it's faster)
3. `fill_application()`: Fill the form with platform-specific selectors, use stealth helpers
4. Add to the `ADAPTER_REGISTRY` list in `adapters/__init__.py`
5. Perform INSERT into the `platform_rate_limits` table (in the migration file)
6. Write `tests/automation/test_<platform>_adapter.py` — `is_matching` and basic form fill tests with a mock page

## Safety
- Only click the submit button when `data["approved"] == True`
- Call `take_snapshot()` before and after submit, save the path to `interaction_logs.payload`
- Do not write the `encrypted_session_path` content to any logs or outputs
- The first test must absolutely be done in `headless=False` (visible browser) mode
