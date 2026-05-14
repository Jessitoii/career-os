import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base

class ApplicationStatus(str, enum.Enum):
    scraped = 'scraped'
    scored = 'scored'
    pending_approval = 'pending_approval'
    approved = 'approved'
    applying = 'applying'
    applied = 'applied'
    interview = 'interview'
    rejected = 'rejected'
    ghosted = 'ghosted'
    withdrawn = 'withdrawn'
    offer = 'offer'
    pending_later = 'pending_later'
    failed = 'failed'

class Application(Base):
    __tablename__ = 'applications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('job_listings.id', ondelete='CASCADE'))
    profile_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id', ondelete='CASCADE'))
    cv_id = Column(UUID(as_uuid=True), ForeignKey('cv_documents.id'))

    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.scraped)
    last_status_change = Column(DateTime(timezone=True), default=datetime.utcnow)
    rejection_reason = Column(String)
    is_manual_entry = Column(Boolean, default=False)
    
    applied_at = Column(DateTime(timezone=True))
    interview_date = Column(DateTime(timezone=True))
    
    application_data = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('job_id', 'profile_id', name='uq_job_profile'),
    )

    job = relationship("JobListing", back_populates="applications")
    profile = relationship("UserProfile", back_populates="applications")
    cv = relationship("CVDocument", back_populates="applications")
    logs = relationship("InteractionLog", back_populates="application", cascade="all, delete-orphan")


class InteractionLog(Base):
    __tablename__ = 'interaction_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey('applications.id', ondelete='CASCADE'))
    actor = Column(String, nullable=False) # 'system', 'user', 'browser_agent', 'recruiter'
    action_type = Column(String, nullable=False)
    content = Column(String)
    payload = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    application = relationship("Application", back_populates="logs")
