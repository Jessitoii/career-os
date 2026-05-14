import logging
import time
from redis import Redis
from app.core.config import settings
from app.hitl.telegram_bot import get_bot_application

logger = logging.getLogger(__name__)
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

class AlertManager:
    """
    Operator-grade alerting with severity levels and deduplication cooling windows.
    """
    
    COOLDOWN_WINDOWS = {
        "WARNING": 3600,  # 1 hour
        "CRITICAL": 300,  # 5 mins
    }

    @classmethod
    async def send_alert(cls, title: str, message: str, severity: str = "WARNING", dedupe_key: str = None):
        if not dedupe_key:
            dedupe_key = f"{title}:{message}"
            
        redis_key = f"alert_cooldown:{severity}:{dedupe_key}"
        
        # Deduplication check
        if redis_client.exists(redis_key):
            logger.debug(f"Alert '{title}' suppressed by deduplication cooling window.")
            return
            
        # Set cooldown
        cooldown = cls.COOLDOWN_WINDOWS.get(severity, 3600)
        redis_client.set(redis_key, "1", ex=cooldown)
        
        # Log it
        if severity == "CRITICAL":
            logger.critical(f"ALERT [{severity}] {title}: {message}")
        else:
            logger.warning(f"ALERT [{severity}] {title}: {message}")
            
        # Telegram Notification
        if settings.TELEGRAM_CHAT_ID:
            icon = "🚨" if severity == "CRITICAL" else "⚠️"
            text = f"{icon} **{severity} ALERT**: {title}\n\n{message}"
            
            try:
                bot_app = get_bot_application()
                if bot_app:
                    await bot_app.bot.send_message(
                        chat_id=settings.TELEGRAM_CHAT_ID,
                        text=text,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Failed to dispatch Telegram alert: {e}")
