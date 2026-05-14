import asyncio
import psutil
import logging
import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, BrowserContext
from app.core.config import settings

logger = logging.getLogger(__name__)

class BrowserPoolManager:
    """
    Hardened browser resource manager.
    Isolates risk levels, enforces memory thresholds, and cleans up zombie contexts.
    """
    
    def __init__(self, max_concurrent: int = 3, max_memory_mb: int = 2000):
        self.max_concurrent = max_concurrent
        self.max_memory_mb = max_memory_mb
        self._active_contexts = 0
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._playwright_instance = None
        
    async def _init_playwright(self):
        if not self._playwright_instance:
            self._playwright_instance = await async_playwright().start()

    def check_memory(self):
        """Monitor total memory. Playwright leaks will kill long-running workers."""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)
        if mem_mb > self.max_memory_mb:
            logger.critical(f"Memory threshold exceeded: {mem_mb:.2f}MB > {self.max_memory_mb}MB. Forcing garbage collection and pool reset.")
            raise MemoryError("Browser memory threshold exceeded. Recycling pool.")

    @asynccontextmanager
    async def acquire_context(self, platform_id: str, risk_level: str = "normal") -> BrowserContext:
        """
        Acquires an isolated browser context.
        Pools are isolated by ATS type (platform_id) AND risk_level.
        """
        await self._semaphore.acquire()
        self._active_contexts += 1
        
        try:
            self.check_memory()
            await self._init_playwright()
            
            # Isolate the user data dir based on platform AND risk to prevent contaminated contexts
            safe_platform_id = f"{platform_id}_{risk_level}"
            platform_dir = os.path.join(settings.TRACE_DIR, "browser_profiles", safe_platform_id)
            os.makedirs(platform_dir, exist_ok=True)
            
            args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--no-sandbox'
            ]
            
            logger.info(f"Launching browser context for {safe_platform_id}")
            context = await self._playwright_instance.chromium.launch_persistent_context(
                user_data_dir=platform_dir,
                headless=settings.PLAYWRIGHT_HEADLESS,
                slow_mo=settings.PLAYWRIGHT_SLOW_MO,
                args=args,
                viewport={'width': 1280, 'height': 800}
            )
            
            yield context
            
        except Exception as e:
            logger.error(f"Browser Pool Error: {e}")
            raise
        finally:
            if 'context' in locals():
                await context.close()
            self._active_contexts -= 1
            self._semaphore.release()
            
            # Aggressive cleanup if pool is empty
            if self._active_contexts == 0 and self._playwright_instance:
                await self._playwright_instance.stop()
                self._playwright_instance = None
                import gc
                gc.collect()

browser_pool = BrowserPoolManager(max_concurrent=3)
