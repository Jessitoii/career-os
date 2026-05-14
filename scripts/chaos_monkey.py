import os
import random
import time
import logging
import subprocess

logger = logging.getLogger(__name__)

class ChaosMonkey:
    def __init__(self):
        self.destructive_mode = os.getenv("CHAOS_DESTRUCTIVE", "false").lower() == "true"
        
    def inject_simulated_fault(self, probability: float = 0.1):
        """Safe simulation mode: injects python-level exceptions."""
        if random.random() < probability:
            faults = [
                ConnectionError("Simulated Redis timeout"),
                TimeoutError("Simulated Playwright execution timeout"),
                ValueError("Simulated bad DOM state")
            ]
            fault = random.choice(faults)
            logger.warning(f"CHAOS MONKEY (SAFE): Injecting fault -> {fault}")
            raise fault

    def drop_redis_container(self):
        """Destructive mode: forcefully kills Redis."""
        self._enforce_destructive_guardrails()
        logger.critical("CHAOS MONKEY (DESTRUCTIVE): Killing Redis container...")
        subprocess.run(["docker", "stop", "careeros-redis-1"], check=False)
        time.sleep(30) # leave it dead for 30s
        logger.critical("CHAOS MONKEY (DESTRUCTIVE): Restarting Redis container...")
        subprocess.run(["docker", "start", "careeros-redis-1"], check=False)

    def _enforce_destructive_guardrails(self):
        if not self.destructive_mode:
            raise PermissionError("Destructive chaos mode is disabled. Set CHAOS_DESTRUCTIVE=true")
        if os.getenv("ENVIRONMENT") == "production":
            raise PermissionError("NEVER run destructive chaos testing in production.")
            
chaos = ChaosMonkey()
