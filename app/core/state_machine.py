import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationStatus, InteractionLog

logger = logging.getLogger(__name__)

class StateMachineError(Exception):
    pass

# Valid transitions map
VALID_TRANSITIONS = {
    ApplicationStatus.scraped: [ApplicationStatus.scored, ApplicationStatus.rejected, ApplicationStatus.rejected_blacklist],
    ApplicationStatus.scored: [
        ApplicationStatus.pending_approval, 
        ApplicationStatus.approved, 
        ApplicationStatus.rejected,
        ApplicationStatus.rejected_blacklist,
        ApplicationStatus.failed_scoring
    ],
    ApplicationStatus.pending_approval: [
        ApplicationStatus.approved, 
        ApplicationStatus.rejected, 
        ApplicationStatus.pending_later,
        ApplicationStatus.rejected_blacklist
    ],
    ApplicationStatus.pending_later: [ApplicationStatus.approved, ApplicationStatus.rejected],
    ApplicationStatus.approved: [ApplicationStatus.applying, ApplicationStatus.withdrawn, ApplicationStatus.retry_pending],
    ApplicationStatus.applying: [
        ApplicationStatus.applied, 
        ApplicationStatus.failed_apply, 
        ApplicationStatus.requires_human,
        ApplicationStatus.blocked,
        ApplicationStatus.retry_pending
    ],
    ApplicationStatus.applied: [ApplicationStatus.interview, ApplicationStatus.rejected, ApplicationStatus.ghosted],
    
    # Rollback & Error states
    ApplicationStatus.failed_apply: [ApplicationStatus.retry_pending, ApplicationStatus.rejected],
    ApplicationStatus.retry_pending: [ApplicationStatus.applying, ApplicationStatus.rejected, ApplicationStatus.rejected_blacklist],
    ApplicationStatus.requires_human: [ApplicationStatus.approved, ApplicationStatus.rejected],
    ApplicationStatus.blocked: [ApplicationStatus.retry_pending, ApplicationStatus.rejected],
    
    ApplicationStatus.failed_scoring: [ApplicationStatus.scored, ApplicationStatus.rejected],
    
    # Terminal states
    ApplicationStatus.interview: [ApplicationStatus.offer, ApplicationStatus.rejected],
    ApplicationStatus.offer: [],
    ApplicationStatus.rejected: [],
    ApplicationStatus.rejected_blacklist: [],
    ApplicationStatus.ghosted: [],
    ApplicationStatus.withdrawn: []
}

def transition_state(db: Session, application_id: str, new_status: ApplicationStatus, actor: str = 'system', payload: dict = None) -> Application:
    """
    Safely transition an application from one state to another, enforcing validation rules.
    Hard rejects invalid transitions and logs the interaction.
    Uses row-level DB locks to prevent race conditions during Celery worker concurrency.
    """
    from sqlalchemy.exc import OperationalError
    from app.models.event import EventStream
    
    try:
        # CONCURRENCY FIX: Lock the row during the transition so no other worker can touch it
        app = db.query(Application).with_for_update(nowait=True).filter(Application.id == application_id).first()
    except OperationalError:
        logger.warning(f"Could not acquire lock for Application {application_id}. Another process is transitioning it.")
        raise ValueError(f"Application {application_id} is currently locked by another worker.")

    if not app:
        raise ValueError(f"Application {application_id} not found")
        
    current_status = app.status
    allowed_next = VALID_TRANSITIONS.get(current_status, [])
    
    if new_status not in allowed_next:
        error_msg = f"Invalid state transition: {current_status} -> {new_status}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    logger.info(f"Transitioning app {application_id}: {current_status} -> {new_status} (by {actor})")
    
    # Update status and timestamp
    app.status = new_status
    app.last_status_change = datetime.utcnow()
    
    if new_status == ApplicationStatus.applied:
        app.applied_at = datetime.utcnow()
        
    db.add(app)

    # Event Sourcing Append
    event_payload = payload or {}
    event_payload["from_status"] = current_status.value
    event_payload["to_status"] = new_status.value
    
    event = EventStream(
        event_type="STATE_TRANSITION",
        entity_id=str(app.id),
        actor=actor,
        payload=event_payload
    )
    db.add(event)
        
    db.add(app)

    # Log interaction
    log_entry = InteractionLog(
        application_id=app.id,
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
