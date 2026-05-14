import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base

class JobListing(Base):
    __tablename__ = 'job_listings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    location = Column(String)
    salary_raw = Column(String)
    salary_min = Column(Numeric)
    salary_max = Column(Numeric)
    description_text = Column(String)
    url = Column(String, unique=True, nullable=False)

    relevance_score = Column(Integer)
    relevance_reasoning = Column(ARRAY(TEXT))
    detected_stack = Column(ARRAY(TEXT))

    embedding = Column(Vector(384))

    status = Column(String, default='new')
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
