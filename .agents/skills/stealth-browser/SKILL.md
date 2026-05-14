---
name: stealth-browser
description: Use when implementing or debugging anti-bot evasion for Playwright browser automation. Triggers on: "stealth", "bot detection", "fingerprint", "Cloudflare block", "DataDome", "PerimeterX", "human typing", "mouse jitter", "natural scroll", "user-agent rotation", "WebGL randomization", "Canvas fingerprint", "hardwareConcurrency", "gaussian jitter", "keystroke latency", "playwright-stealth", "browser fingerprint", "anti-bot", "bot detection bypass".
---

# Stealth Browser Skill

## Use this skill when
- Setting up or updating the stealth layer for the Playwright session
- Implementing human-like typing (human_type), clicking (human_click), or scrolling (natural_scroll)
- Debugging when stuck by a bot detection block (Cloudflare, DataDome, PerimeterX)
- Randomizing browser fingerprints (UA, WebGL, Canvas, hardware signals)
- Adjusting the wait/jitter timing between sessions

## Do not use this skill when
- Writing an ATS-specific form selector → use the `ats-adapter` skill
- Configuring platform-based rate limits → use the `db-schema` skill (platform_rate_limits table)

---

## Source File: app/automation/stealth.py

All stealth helpers are gathered in this single file. Other modules import from here.

```python
"""
app/automation/stealth.py
All anti-bot evasion helpers. Do not make direct Playwright calls — use these.
"""
import random
import asyncio
import time
from playwright.async_api import Page, BrowserContext

# ─────────────────────────────────────────────
# 1. TIMING HELPERS
# ─────────────────────────────────────────────

async def gaussian_wait(mu: float = 2.0, sigma: float = 0.5, min_wait: float = 0.3) -> None:
    """
    DO NOT use constant sleep(). Always call this.
    Wait time with Gaussian distribution — simulates human behavior.
    """
    wait = max(min_wait, random.gauss(mu, sigma))
    await asyncio.sleep(wait)


async def human_type(page: Page, selector: str, text: str) -> None:
    """
    Typing with variable delay between each character.
    Includes a 5% chance of simulating typing a wrong character and deleting it.
    """
    await page.focus(selector)
    await asyncio.sleep(random.uniform(0.1, 0.3))  # micro-pause after focus

    for char in text:
        await page.type(selector, char, delay=random.randint(50, 150))
        # Typo simulation: 5% chance to make a mistake and correct it
        if random.random() > 0.95:
            await asyncio.sleep(random.uniform(0.1, 0.4))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.08, 0.2))
            await page.type(selector, char, delay=random.randint(60, 130))


async def human_click(page: Page, selector: str) -> None:
    """
    Click at a random point inside the button, not exactly in the center.
    The mouse movement occurs in multiple steps (non-linear).
    """
    element = page.locator(selector).first
    box = await element.bounding_box()
    if not box:
        # Fallback: standard click
        await element.click()
        return

    # Random point inside the element (in the 20%-80% range, away from the edges)
    x = box["x"] + random.uniform(box["width"] * 0.2, box["width"] * 0.8)
    y = box["y"] + random.uniform(box["height"] * 0.2, box["height"] * 0.8)

    # Move the mouse in multiple steps
    await page.mouse.move(x, y, steps=random.randint(8, 20))
    await asyncio.sleep(random.uniform(0.05, 0.2))
    await page.mouse.click(x, y)


async def natural_scroll(page: Page) -> None:
    """
    A pattern that simulates reading speed instead of linear scrolling:
    - Variable step sizes
    - Pauses in between
    - Occasionally scrolling back up slightly
    """
    current_pos = 0
    target = await page.evaluate("document.body.scrollHeight")

    while current_pos < target:
        step = random.randint(200, 500)
        await page.mouse.wheel(0, step)
        current_pos += step

        # 15% chance to scroll back up slightly (reading behavior)
        if random.random() > 0.85:
            back = random.randint(50, 150)
            await page.mouse.wheel(0, -back)
            current_pos -= back

        await asyncio.sleep(random.uniform(0.5, 1.8))


async def mouse_jiggle(page: Page, duration_seconds: float = 2.0) -> None:
    """
    Small natural mouse jitters in empty areas while filling out the form.
    Makes random small movements to anywhere on the form.
    """
    viewport = page.viewport_size or {"width": 1280, "height": 720}
    end_time = time.time() + duration_seconds

    while time.time() < end_time:
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(x, y, steps=random.randint(3, 8))
        await asyncio.sleep(random.uniform(0.2, 0.8))


# ─────────────────────────────────────────────
# 2. FINGERPRINT EVASION
# ─────────────────────────────────────────────

def get_stealth_init_script(concurrency: int = None, gpu_vendor: str = None, gpu_renderer: str = None) -> str:
    """
    The JS to be injected with page.add_init_script() in every session.
    Parameters are chosen randomly — a different fingerprint for each session.
    """
    concurrency = concurrency or random.choice([4, 6, 8, 12])
    gpu_vendor   = gpu_vendor   or random.choice(["Intel Inc.", "NVIDIA Corporation", "AMD"])
    gpu_renderer = gpu_renderer or random.choice([
        "Intel Iris OpenGL Engine",
        "NVIDIA GeForce RTX 3060/PCIe/SSE2",
        "AMD Radeon RX 6700 XT",
        "Intel UHD Graphics 620",
    ])

    return f"""
    // remove the webdriver flag
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});

    // randomize hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {concurrency} }});

    // WebGL fingerprint — real GPU simulation
    const _getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return '{gpu_vendor}';    // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return '{gpu_renderer}';  // UNMASKED_RENDERER_WEBGL
        return _getParam.call(this, param);
    }};

    // Battery API — make it look like it's charging
    if (navigator.getBattery) {{
        navigator.getBattery = async () => ({{
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: {round(random.uniform(0.6, 1.0), 2)},
            addEventListener: () => {{}},
        }});
    }}

    // Chrome runtime (for Chromium bot detection)
    window.chrome = {{ runtime: {{}} }};

    // Permissions API — show the camera/microphone prompt normally
    const _query = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        (params.name === 'notifications')
            ? Promise.resolve({{ state: Notification.permission }})
            : _query(params);
    """


REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

REALISTIC_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 800},
]


# ─────────────────────────────────────────────
# 3. SESSION SETUP
# ─────────────────────────────────────────────

async def create_stealth_context(playwright, user_data_dir: str) -> BrowserContext:
    """
    Create a stealth-patched Chromium context.
    Persistent session with user_data_dir — LinkedIn/Google session is preserved.
    """
    ua = random.choice(REALISTIC_USER_AGENTS)
    viewport = random.choice(REALISTIC_VIEWPORTS)

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=True,   # Production: True | Debug: False
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            f"--window-size={viewport['width']},{viewport['height']}",
        ],
        user_agent=ua,
        viewport=viewport,
        locale="en-US",
        timezone_id="Europe/Berlin",
    )

    # Inject the Stealth script into all new pages
    await context.add_init_script(get_stealth_init_script())

    return context
```

---

## Session Setup Checklist

Before opening a new browser session, verify the following:

1. The context was created with `create_stealth_context()` (not raw `playwright.chromium.launch()`)
2. `add_init_script(get_stealth_init_script())` was injected
3. The User-Agent was randomly selected for this session
4. The Viewport was randomly selected for this session
5. `user_data_dir` is read from the encrypted path (`encrypted_session_path` column), its value is not written to the logs

## Bot Detection Debug Steps

When stuck by a bot detection block, check the following in order:

1. Go to https://bot.sannysoft.com — the fingerprint test page
2. Verify that the `navigator.webdriver` value returns `undefined`
3. Check that the WebGL vendor/renderer looks realistic
4. Verify that all `sleep()` calls have been replaced with `gaussian_wait()`
5. Verify that the typing delays use `human_type()`

## Safety
- Do not write the `user_data_dir` path to any log, terminal output, or API response
- `headless=False` is only for development/debug; it must always be `True` in production
- The Stealth init script is automatically injected at every new page opening (context level) — do not add it again at the page level
