---
description: Create a browser automation adapter for a new ATS platform.
---

## Usage
```
/new-adapter <platform_name> <url_detection_pattern>
```

**Example:** `/new-adapter ashby .ashbyhq.com`

## Steps

### 1. Load the ats-adapter skill
Before running this workflow, read the `ats-adapter` skill — for the base class,
AdapterRegistry, and fallback hierarchy.

### 2. Create the Adapter File
Create the `app/automation/adapters/<platform_name>.py` file:

```python
from playwright.async_api import Page
from .base import ATSAdapter
from ..stealth import human_type, human_click, gaussian_wait

class <PlatformName>Adapter(ATSAdapter):
    async def is_matching(self) -> bool:
        return "<url_detection_pattern>" in self.page.url

    async def fill_application(self, data: dict) -> None:
        # TODO: fill the form with platform-specific selectors
        # use stealth helpers: human_type, human_click, gaussian_wait
        # DO NOT submit unless data["approved"] == True
        pass
```

### 3. Register in AdapterRegistry
Add to the `app/automation/adapters/__init__.py` file:
```python
from .<platform_name> import <PlatformName>Adapter
ADAPTER_REGISTRY = [..., <PlatformName>Adapter]
```

### 4. Add Rate Limit to DB
In the migration file or directly:
```sql
INSERT INTO platform_rate_limits (platform, min_wait_seconds, max_wait_seconds, daily_cap, notes)
VALUES ('<platform_name>', 60, 300, 30, 'Initial deployment — conservative values');
```

### 5. Write Tests
Create the `tests/automation/test_<platform_name>_adapter.py` file:
- `is_matching()` validation test (with mock URL)
- `fill_application()` basic field tests (with mock page)

### 6. Test in Headed Mode
```python
# temporarily in create_stealth_context() inside stealth.py:
headless=False  # Show the browser
```
Test the form on the real portal, observe the accuracy of the selectors.

## Expected Outputs
- `app/automation/adapters/<platform_name>.py`
- `ADAPTER_REGISTRY` update
- DB rate limit record
- `tests/automation/test_<platform_name>_adapter.py`

## Notes
- Use the `pierce/` selector pattern from the `ats-adapter` skill for portals containing a Shadow DOM
- The first test must be done with `headless=False` — you must observe the selectors
- Do not use a real job listing when testing the submit button — create a test account
