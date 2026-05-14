import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationStatus, InteractionLog

logger = logging.getLogger(__name__)

class StateMachineError(Exception):
    pass

# Valid transitions map
VALID_TRANSITIONS = {
    ApplicationStatus.scraped: [ApplicationStatus.scored, ApplicationStatus.rejected],
    ApplicationStatus.scored: [
        ApplicationStatus.pending_approval, 
        ApplicationStatus.approved, 
        ApplicationStatus.rejected
    ],
    ApplicationStatus.pending_approval: [
        ApplicationStatus.approved, 
        ApplicationStatus.rejected, 
        ApplicationStatus.pending_later
    ],
    ApplicationStatus.pending_later: [ApplicationStatus.approved, ApplicationStatus.rejected],
    ApplicationStatus.approved: [ApplicationStatus.applying, ApplicationStatus.withdrawn],
    ApplicationStatus.applying: [ApplicationStatus.applied, ApplicationStatus.failed],
    ApplicationStatus.applied: [ApplicationStatus.interview, ApplicationStatus.rejected, ApplicationStatus.ghosted],
    ApplicationStatus.failed: [ApplicationStatus.applying], # retry
    ApplicationStatus.interview: [ApplicationStatus.offer, ApplicationStatus.rejected],
    ApplicationStatus.offer: [],
    ApplicationStatus.rejected: [],
    ApplicationStatus.ghosted: [],
    ApplicationStatus.withdrawn: []
}

def transition_state(db: Session, application_id: str, new_status: ApplicationStatus, actor: str = "system", payload: dict = None):
    """
    Transition an application to a new state, enforcing valid transitions and logging the change.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ValueError(f"Application {application_id} not found")

    current_status = application.status

    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise StateMachineError(f"Invalid transition from {current_status} to {new_status}")

    # Apply transition
    application.status = new_status
    application.last_status_change = datetime.utcnow()
    
    if new_status == ApplicationStatus.applied:
        application.applied_at = datetime.utcnow()
        
    db.add(application)

    # Log interaction
    log_entry = InteractionLog(
        application_id=application.id,
        actor=actor,
        action_type="state_transition",
        content=f"Transitioned from {current_status.value} to {new_status.value}",
        payload=payload or {}
    )
    db.add(log_entry)
    
    db.commit()
    db.refresh(application)
    
    logger.info(f"[{application_id}] State changed: {current_status.value} -> {new_status.value}")
    
    return application
