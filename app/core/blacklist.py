import logging
from sqlalchemy.orm import Session
from app.models.blacklist import CompanyBlacklist
from app.models.application import Application, ApplicationStatus
from app.models.job import JobListing

logger = logging.getLogger(__name__)

def add_to_blacklist(db: Session, company_name: str, domain: str = None, reason: str = "User triggered", is_permanent: bool = True):
    """
    Adds a company to the blacklist and instantly cascades a soft-block rejection 
    across all pending applications for this company.
    """
    # 1. Add to blacklist table
    bl = db.query(CompanyBlacklist).filter(CompanyBlacklist.company_name == company_name).first()
    if not bl:
        bl = CompanyBlacklist(company_name=company_name, domain_match=domain, is_permanent=is_permanent, reason=reason)
        db.add(bl)
        db.commit()

    # 2. Cascade soft-reject to existing apps (never touch 'applied' or 'interview' states)
    # Target states: scraped, scored, pending_approval, retry_pending, applying (if queue allows interruption)
    target_states = [
        ApplicationStatus.scraped, 
        ApplicationStatus.scored, 
        ApplicationStatus.pending_approval, 
        ApplicationStatus.retry_pending,
        ApplicationStatus.failed_apply,
        ApplicationStatus.blocked
    ]
    
    # We find all jobs matching the company
    jobs = db.query(JobListing).filter(JobListing.company_name.ilike(f"%{company_name}%")).all()
    job_ids = [j.id for j in jobs]
    
    if not job_ids:
        return
        
    apps = db.query(Application).filter(Application.job_id.in_(job_ids), Application.status.in_(target_states)).all()
    
    for app in apps:
        app.status = ApplicationStatus.rejected_blacklist
        app.rejection_reason = f"Blacklisted: {reason}"
        db.add(app)
        
    db.commit()
    logger.info(f"Blacklisted {company_name}. Soft-rejected {len(apps)} pending applications.")

def is_blacklisted(db: Session, company_name: str) -> bool:
    """Check if a company is currently blacklisted."""
    bl = db.query(CompanyBlacklist).filter(CompanyBlacklist.company_name.ilike(f"%{company_name}%")).first()
    return bl is not None
