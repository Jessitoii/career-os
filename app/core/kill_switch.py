import logging
from redis import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

def engage_kill_switch(reason: str = "Manual Emergency Pause"):
    redis_client.set(settings.GLOBAL_KILL_SWITCH_KEY, "PAUSED")
    logger.critical(f"GLOBAL KILL SWITCH ENGAGED: {reason}")

def disengage_kill_switch():
    redis_client.delete(settings.GLOBAL_KILL_SWITCH_KEY)
    logger.info("Global kill switch disengaged. Automation resuming.")

def is_paused() -> bool:
    return redis_client.exists(settings.GLOBAL_KILL_SWITCH_KEY) > 0
