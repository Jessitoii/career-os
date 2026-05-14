import hashlib
import logging
from typing import Dict, Any
from app.core.config import settings
from redis import Redis

logger = logging.getLogger(__name__)

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

class FeatureFlags:
    """
    Manages deterministic cohort assignment for canary rollouts.
    Does NOT randomize blindly. Uses (ATS type, company domain, job category, app_id) to shard traffic.
    """
    
    @staticmethod
    def _deterministic_hash(shard_key: str) -> int:
        """Returns a stable 0-99 integer based on the shard key."""
        hash_hex = hashlib.sha256(shard_key.encode('utf-8')).hexdigest()
        return int(hash_hex, 16) % 100

    @classmethod
    def is_enabled(cls, flag_name: str, ats_type: str, company: str, application_id: str, default_pct: int = 0) -> bool:
        """
        Determines if a feature is enabled for a specific application.
        Check Redis for a snapshot first to prevent retroactive mutation.
        """
        snapshot_key = f"ff_snapshot:{application_id}:{flag_name}"
        
        # 1. Check if we already evaluated this flag for this application (Prevents retroactive mutation on replay)
        cached_result = redis_client.get(snapshot_key)
        if cached_result is not None:
            return cached_result == "1"

        # 2. Get global rollout percentage from Redis (fallback to default_pct)
        rollout_pct_key = f"ff_pct:{flag_name}"
        pct_str = redis_client.get(rollout_pct_key)
        pct = int(pct_str) if pct_str is not None else default_pct

        if pct == 0:
            result = False
        elif pct >= 100:
            result = True
        else:
            # 3. Deterministic Cohort Sharding
            # We want the same company + ATS type to behave identically most of the time to train the selector DB
            # but we mix in the application_id slightly so we don't block 100% of a company if a flag is bad.
            shard_key = f"{ats_type}:{company}:{application_id}"
            bucket = cls._deterministic_hash(shard_key)
            result = bucket < pct
            
        # Snapshot the result forever
        redis_client.set(snapshot_key, "1" if result else "0")
        
        logger.debug(f"Feature Flag '{flag_name}' evaluated to {result} for App {application_id} (Pct: {pct}%)")
        return result

    @classmethod
    def set_rollout_percentage(cls, flag_name: str, percentage: int):
        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be 0-100")
        redis_client.set(f"ff_pct:{flag_name}", percentage)
        logger.warning(f"Feature Flag '{flag_name}' rollout set to {percentage}%")
