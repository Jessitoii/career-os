# **Job Application Agent: Automation & Stealth Playbook**

This document defines the architecture and strategies required for reliability and bypassing anti-bot obstacles in browser automation.

## **1. ATS Adapter Pattern Architecture**

Different application systems (Greenhouse, Lever, Workday) have different DOM structures. The **Adapter Pattern** should be used to manage these from a single center.

### **Base Adapter and Specific Implementations**

```python
from abc import ABC, abstractmethod  
from playwright.async_api import Page

class ATSAdapter(ABC):  
    def __init__(self, page: Page):  
        self.page = page

    @abstractmethod  
    async def is_matching(self) -> bool:  
        """Determines whether the page belongs to this ATS."""  
        pass

    @abstractmethod  
    async def fill_application(self, data: dict):  
        """Logic for filling the form."""  
        pass

class GreenhouseAdapter(ATSAdapter):  
    async def is_matching(self) -> bool:  
        return "boards.greenhouse.io" in self.page.url

    async def fill_application(self, data: dict):  
        # Greenhouse-specific selectors  
        await self.page.fill("input#first_name", data['first_name'])  
        await self.page.set_input_files("input[type='file']", data['cv_path'])  
        # ...

class WorkdayAdapter(ATSAdapter):  
    async def is_matching(self) -> bool:  
        return ".myworkdayjobs.com" in self.page.url

    async def fill_application(self, data: dict):  
        # Workday contains shadow DOM and dynamic loading, requires more complex selector management  
        pass
```

## **2. Stealth Strategy: Anti-Bot Evasion**

Bot detection systems (Cloudflare, Datadome, etc.) generally look at three things: **Technical Fingerprint**, **Timing**, and **Behavior**.

### **A. Fingerprinting Evasion**

Using playwright-stealth alone is not enough. The following parameters need to be randomized in each session:

* **User-Agent:** Should not just be a string, but compatible with navigator.userAgentData.  
* **WebGL & Canvas:** Graphics card rendering parameters should simulate a real device.  
* **Battery & Hardware Concurrency:** Passive signals like navigator.hardwareConcurrency and battery status.

### **B. Timing Analysis**

Using a fixed wait(2000) is the fastest way to get caught.

* **Gaussian Jitter:** Wait times should be calculated with random.gauss(mu, sigma).  
* **Variable Typing Speed:** Millisecond-level, variable delays (keystroke latency) should be added between each character.

### **C. Random Human-Like Behavior**

* **Pixel-Perfect Clicking:** Clicking at a random (but naturally distributed) point within the button area, not exactly in the center of the button.  
* **Non-Linear Scrolling:** Instead of scrolling straight down, scroll patterns that simulate reading speed, sometimes pausing or slightly scrolling up.  
* **Mouse Jiggling:** The mouse making small, natural jitters in empty areas while filling out the form.

## **3. Unknown UI & Fallback Mechanism**

When the system encounters an unrecognized site (Custom Portal), the following hierarchy is followed:

### **Layer 1: Heuristic Mapping (Traditional)**

Dictionary-based matching. label: contains("Name") -> input#id.

### **Layer 2: LLM Vision / DOM Fallback**

If Layer 1 fails:

1. **Snap:** The screenshot and Accessibility Tree of the current page are captured.  
2. **Context:** Sent to the LLM (with Vision capability): *"What is the CSS selector for the 'Salary Expectation' field in this form?"*  
3. **Execute:** The operation is performed with the returned selector.

### **Layer 3: Human-in-the-Loop (Web GUI & Telegram)**

If the LLM is unsure or fails:

* A screenshot of the page is sent to the Web GUI and Telegram.  
* Input or approval is expected from the user.  
* The user's response is saved to the memory system, so that "learned behavior" is applied when encountering the same site again.

## **4. Implementation Example (Stealth Helper)**

```python
import random  
import asyncio

async def human_type(page, selector, text):  
    await page.focus(selector)  
    for char in text:  
        await page.type(selector, char, delay=random.randint(50, 150))  
        if random.random() > 0.95:  # Typo and correction simulation  
            await page.keyboard.press("Backspace")  
            await page.type(selector, char, delay=random.randint(50, 150))

async def natural_scroll(page):  
    current_pos = 0  
    target = await page.evaluate("document.body.scrollHeight")  
    while current_pos < target:  
        step = random.randint(200, 500)  
        await page.mouse.wheel(0, step)  
        current_pos += step  
        await asyncio.sleep(random.uniform(0.5, 1.5))  
```
