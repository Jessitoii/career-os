import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base

class EventStream(Base):
    """
    Append-only event log for forensic reconstruction.
    Captures state transitions, queue actions, kill switch events, and security escalations.
    """
    __tablename__ = 'event_stream'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    correlation_id = Column(String, index=True, nullable=True)
    
    event_type = Column(String, nullable=False, index=True) # e.g., 'STATE_TRANSITION', 'QUEUE_DEADLETTER', 'KILL_SWITCH'
    entity_id = Column(String, index=True) # e.g., application_id, job_id, or "system"
    actor = Column(String) # e.g., 'system', 'telegram', 'chaos_monkey'
    
    payload = Column(JSONB, default=dict)
