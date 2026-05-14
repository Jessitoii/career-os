---
name: stealth-browser
description: Use when implementing or debugging anti-bot evasion for Playwright automation. Triggers on: "bot tespit", "stealth", "fingerprint", "Cloudflare engeli", "Datadome", "human typing", "mouse jitter", "scroll pattern", "user-agent rotasyonu", "WebGL randomization", "rate limit kaçınma", "doğal davranış simülasyonu".
---

# Stealth Browser Skill

## Use this skill when
- Setting up or modifying the Playwright stealth layer
- Implementing human-like typing, mouse movement, or scrolling
- Debugging a bot-detection block (Cloudflare, DataDome, PerimeterX)
- Randomizing browser fingerprints (User-Agent, WebGL, Canvas, hardware signals)
- Tuning wait/jitter timing between actions

## Do not use this skill when
- Writing ATS-specific form selectors (use `ats-adapter` skill)
- Configuring rate limits per platform (use `session-lifecycle` skill)

## Three Detection Vectors (Always Defend All Three)

### 1. Technical Fingerprint
Randomize per session:
- **User-Agent + userAgentData**: Must be consistent — string AND `navigator.userAgentData` must match
- **WebGL Renderer/Vendor**: Inject realistic GPU strings via `page.add_init_script`
- **Canvas Fingerprint**: Add ±1-3px noise to canvas `getImageData` reads
- **hardwareConcurrency**: Randomize between 4, 6, 8, 12
- **Battery API**: Return `charging: true`, level between 0.6–1.0

### 2. Timing Analysis
```python
import random, asyncio

async def human_type(page, selector: str, text: str):
    await page.focus(selector)
    for char in text:
        await page.type(selector, char, delay=random.randint(50, 150))
        # 5% typo-and-correct simulation
        if random.random() > 0.95:
            await page.keyboard.press("Backspace")
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.type(selector, char, delay=random.randint(60, 120))

async def gaussian_wait(mu: float = 2.0, sigma: float = 0.5):
    """Never use fixed sleep(). Always use this."""
    wait = max(0.5, random.gauss(mu, sigma))
    await asyncio.sleep(wait)
```

### 3. Behavioral Patterns
```python
async def natural_scroll(page):
    """Non-linear scrolling that mimics reading behavior."""
    current_pos = 0
    target = await page.evaluate("document.body.scrollHeight")
    while current_pos < target:
        step = random.randint(200, 500)
        await page.mouse.wheel(0, step)
        current_pos += step
        # Occasionally scroll back up slightly (reading behavior)
        if random.random() > 0.85:
            back = random.randint(50, 150)
            await page.mouse.wheel(0, -back)
            current_pos -= back
        await asyncio.sleep(random.uniform(0.5, 1.5))

async def human_click(page, selector: str):
    """Click a random point within the element, not dead-center."""
    el = page.locator(selector)
    box = await el.bounding_box()
    x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
    y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
    await page.mouse.move(x, y, steps=random.randint(5, 15))
    await asyncio.sleep(random.uniform(0.05, 0.2))
    await page.mouse.click(x, y)
```

## Instructions

### Session Setup Checklist
1. Launch browser with `user_data_dir` for persistent auth
2. Apply `playwright-stealth` equivalent patches via `add_init_script`
3. Randomize UA + hardware signals before first navigation
4. Set viewport to a common resolution (1920x1080, 1440x900, 1280x800)
5. Disable `webdriver` flag: `Object.defineProperty(navigator, 'webdriver', {get: () => undefined})`

### Fingerprint Init Script Template
```javascript
// Inject as page.add_init_script(script=...)
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => CONCURRENCY });
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
// Override WebGL renderer
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {
  if (param === 37445) return 'Intel Inc.';   // VENDOR
  if (param === 37446) return 'Intel Iris OpenGL Engine'; // RENDERER
  return getParameter.call(this, param);
};
```

## Safety
- Never share or log the `user_data_dir` path — it contains live session cookies.
- Test stealth config against https://bot.sannysoft.com before deploying to real portals.
