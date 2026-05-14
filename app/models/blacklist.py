import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .base import Base

class CompanyBlacklist(Base):
    __tablename__ = 'company_blacklist'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String, nullable=False, unique=True, index=True)
    domain_match = Column(String, index=True) # e.g. "foo.com"
    reason = Column(String)
    is_permanent = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
