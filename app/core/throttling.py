import time
import random
import logging
from redis import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

class AdaptiveThrottler:
    """
    Manages platform-specific execution pacing and backoff strategies.
    If a CAPTCHA is hit, dynamically increases delay for that specific ATS to avoid fingerprinting.
    """
    
    def __init__(self, platform: str):
        self.platform = platform
        self.delay_key = f"throttle_delay:{platform}"

    def register_captcha_incident(self):
        """Called when ATSAdapter detects a CAPTCHA or block."""
        current_delay = float(redis_client.get(self.delay_key) or 5.0)
        # Exponentially increase delay, cap at 300 seconds
        new_delay = min(current_delay * 2.5, 300.0)
        redis_client.set(self.delay_key, new_delay, ex=86400) # Reset after 24 hours
        logger.warning(f"AdaptiveThrottler: Increased delay for {self.platform} to {new_delay}s due to CAPTCHA.")

    def get_current_delay(self) -> float:
        return float(redis_client.get(self.delay_key) or random.uniform(1.0, 3.0))

    def pace_execution(self):
        """Block execution to respect pacing limits with randomized jitter and circadian behavior."""
        from datetime import datetime
        
        base_delay = self.get_current_delay()
        
        # Circadian Scheduling: Simulate human sleeping hours
        current_hour = datetime.utcnow().hour
        if 0 <= current_hour <= 6:  # Midnight to 6 AM UTC
            logger.info(f"Circadian Throttle: Deep sleep hours. Significantly pacing {self.platform}.")
            base_delay *= random.uniform(3.0, 5.0)
        elif 12 <= current_hour <= 14:  # Lunch break
            base_delay *= random.uniform(1.5, 2.5)
            
        # Random idle periods (5% chance of taking a "coffee break")
        if random.random() < 0.05:
            coffee_break = random.uniform(60.0, 180.0)
            logger.info(f"Circadian Throttle: Taking a simulated break for {coffee_break:.0f}s.")
            base_delay += coffee_break
            
        jitter = random.uniform(0.5, 2.0)
        total_delay = base_delay + jitter
        logger.debug(f"Pacing {self.platform} execution: sleeping for {total_delay:.2f}s")
        time.sleep(total_delay)

def enforce_pacing(platform: str):
    throttler = AdaptiveThrottler(platform)
    throttler.pace_execution()
