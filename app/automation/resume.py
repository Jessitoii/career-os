import os
import hashlib
import logging
from typing import Tuple
from app.core.config import settings
from sqlalchemy.orm import Session
from app.models.user import CVDocument

logger = logging.getLogger(__name__)

def compute_file_hash(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_best_resume(db: Session, job_category: str = None, user_id: str = None) -> Tuple[str, str, str]:
    """
    Returns (strategy_used, resume_path, resume_hash).
    Priority:
    1. Role-specific optimized CV from Document DB
    2. Cached/generated role-family CV
    3. Default master resume
    4. Emergency minimal ATS-safe resume
    """
    # 1. DB Lookup (Optimized)
    if user_id:
        # In a real scenario, filter by job_category/tags
        cv_doc = db.query(CVDocument).filter(CVDocument.user_id == user_id, CVDocument.is_active == True).first()
        if cv_doc and os.path.exists(cv_doc.storage_path):
            return "optimized", cv_doc.storage_path, compute_file_hash(cv_doc.storage_path)

    # 2. Generated Family CV
    if job_category:
        gen_path = os.path.join(settings.RESUME_GENERATED_DIR, f"{job_category}_cv.pdf")
        if os.path.exists(gen_path):
            return "generated", gen_path, compute_file_hash(gen_path)

    # 3. Master Resume
    master_path = os.path.join(settings.RESUME_MASTER_DIR, "master_resume.pdf")
    if os.path.exists(master_path):
        return "master", master_path, compute_file_hash(master_path)

    # 4. Emergency Fallback
    fallback_path = os.path.join(settings.RESUME_FALLBACK_DIR, "emergency_resume.pdf")
    if os.path.exists(fallback_path):
        return "fallback", fallback_path, compute_file_hash(fallback_path)

    logger.error("CRITICAL: No fallback resumes available. System is missing emergency_resume.pdf")
    raise FileNotFoundError("All resume lookups failed, including emergency fallback.")
