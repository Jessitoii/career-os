import logging
from celery import shared_task
from app.core.db import SessionLocal
from app.models.job import JobListing
from app.models.application import Application, ApplicationStatus
from app.intelligence.scoring import score_job_relevance
from app.core.state_machine import transition_state

logger = logging.getLogger(__name__)

@shared_task
def run_daily_session():
    """
    Main entrypoint for the daily agent session.
    1. Scrapes jobs (Discovery)
    2. Scores them (Filtering & Scoring)
    3. Queues applications based on decision (Execution/HitL)
    """
    logger.info("🚀 Session started. Scanning sources...")
    
    db = SessionLocal()
    try:
        # 1. Scraping would be invoked here via playwright scripts
        # async_to_sync(run_scrapers)(db)
        
        # 2. Score un-scored jobs
        new_jobs = db.query(JobListing).filter(JobListing.status == 'new').limit(50).all()
        for job in new_jobs:
            # Sync wrapper for async scoring
            import asyncio
            score_result = asyncio.run(score_job_relevance("Backend Developer with Python", job.title))
            
            job.relevance_score = score_result.score
            job.relevance_reasoning = score_result.reasoning
            job.status = 'scored'
            db.commit()
            
            # 3. Create application entry
            app_status = ApplicationStatus.rejected
            if score_result.decision == "auto_apply":
                app_status = ApplicationStatus.approved
            elif score_result.decision == "ask_user":
                app_status = ApplicationStatus.pending_approval
                
            # Note: profile_id and cv_id would be resolved properly here
            if app_status != ApplicationStatus.rejected:
                # TODO: send telegram hitl if pending_approval
                pass
                
        logger.info("Session complete.")
    finally:
        db.close()
