import os
import glob
import time
import logging
from app.core.config import settings
from celery import shared_task

logger = logging.getLogger(__name__)

# 7 days in seconds
RETENTION_PERIOD = 7 * 24 * 60 * 60

@shared_task(queue="observability")
def prune_old_traces():
    """
    Scheduled task to clean up old Playwright traces and screenshots to prevent disk explosion.
    """
    now = time.time()
    deleted_count = 0
    bytes_freed = 0
    
    # Prune traces
    for file_path in glob.glob(os.path.join(settings.TRACE_DIR, "*.zip")):
        if os.path.isfile(file_path):
            if os.stat(file_path).st_mtime < now - RETENTION_PERIOD:
                bytes_freed += os.path.getsize(file_path)
                os.remove(file_path)
                deleted_count += 1
                
    # Prune screenshots
    for file_path in glob.glob(os.path.join(settings.TRACE_DIR, "*.png")):
        if os.path.isfile(file_path):
            if os.stat(file_path).st_mtime < now - RETENTION_PERIOD:
                bytes_freed += os.path.getsize(file_path)
                os.remove(file_path)
                deleted_count += 1
                
    logger.info(f"Storage Lifecycle: Pruned {deleted_count} files. Freed {bytes_freed / (1024*1024):.2f} MB.")
    return {"deleted": deleted_count, "mb_freed": bytes_freed / (1024*1024)}
