import random
import asyncio
import time
from playwright.async_api import Page, BrowserContext

# ─────────────────────────────────────────────
# 1. TIMING HELPERS
# ─────────────────────────────────────────────

async def gaussian_wait(mu: float = 2.0, sigma: float = 0.5, min_wait: float = 0.3) -> None:
    """Wait time with Gaussian distribution to simulate human behavior."""
    wait = max(min_wait, random.gauss(mu, sigma))
    await asyncio.sleep(wait)


async def human_type(page: Page, selector: str, text: str) -> None:
    """Typing with variable delay and occasional simulated typos."""
    await page.focus(selector)
    await asyncio.sleep(random.uniform(0.1, 0.3))

    for char in text:
        await page.type(selector, char, delay=random.randint(50, 150))
        # 5% chance to make a mistake and correct it
        if random.random() > 0.95:
            await asyncio.sleep(random.uniform(0.1, 0.4))
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.08, 0.2))
            await page.type(selector, char, delay=random.randint(60, 130))


async def human_click(page: Page, selector: str) -> None:
    """Click at a random point inside the button bounds with non-linear mouse movement."""
    element = page.locator(selector).first
    box = await element.bounding_box()
    if not box:
        await element.click()
        return

    x = box["x"] + random.uniform(box["width"] * 0.2, box["width"] * 0.8)
    y = box["y"] + random.uniform(box["height"] * 0.2, box["height"] * 0.8)

    await page.mouse.move(x, y, steps=random.randint(8, 20))
    await asyncio.sleep(random.uniform(0.05, 0.2))
    await page.mouse.click(x, y)


async def natural_scroll(page: Page) -> None:
    """Simulate reading speed and non-linear scrolling."""
    current_pos = 0
    target = await page.evaluate("document.body.scrollHeight")

    while current_pos < target:
        step = random.randint(200, 500)
        await page.mouse.wheel(0, step)
        current_pos += step

        if random.random() > 0.85:
            back = random.randint(50, 150)
            await page.mouse.wheel(0, -back)
            current_pos -= back

        await asyncio.sleep(random.uniform(0.5, 1.8))

async def mouse_jiggle(page: Page, duration_seconds: float = 2.0) -> None:
    """Natural mouse jitters in empty areas."""
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
    """JS to randomize fingerprinting APIs per session."""
    concurrency = concurrency or random.choice([4, 6, 8, 12])
    gpu_vendor = gpu_vendor or random.choice(["Intel Inc.", "NVIDIA Corporation", "AMD"])
    gpu_renderer = gpu_renderer or random.choice([
        "Intel Iris OpenGL Engine",
        "NVIDIA GeForce RTX 3060/PCIe/SSE2",
        "AMD Radeon RX 6700 XT",
        "Intel UHD Graphics 620",
    ])

    return f"""
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {concurrency} }});

    const _getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return '{gpu_vendor}';
        if (param === 37446) return '{gpu_renderer}';
        return _getParam.call(this, param);
    }};

    if (navigator.getBattery) {{
        navigator.getBattery = async () => ({{
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: {round(random.uniform(0.6, 1.0), 2)},
            addEventListener: () => {{}},
        }});
    }}

    window.chrome = {{ runtime: {{}} }};

    const _query = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        (params.name === 'notifications')
            ? Promise.resolve({{ state: Notification.permission }})
            : _query(params);
    """

REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

REALISTIC_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
]

# ─────────────────────────────────────────────
# 3. SESSION SETUP
# ─────────────────────────────────────────────

async def create_stealth_context(playwright, user_data_dir: str, headless: bool = True) -> BrowserContext:
    """Create a stealth-patched Chromium context."""
    ua = random.choice(REALISTIC_USER_AGENTS)
    viewport = random.choice(REALISTIC_VIEWPORTS)

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        headless=headless,
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

    await context.add_init_script(get_stealth_init_script())
    return context
