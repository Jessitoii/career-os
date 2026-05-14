import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base

class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    preferences = Column(JSONB, default=lambda: {
        "target_roles": [],
        "min_salary": 0,
        "remote_preference": "hybrid",
        "blocked_companies": []
    })
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    cvs = relationship("CVDocument", back_populates="profile", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="profile", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="profile", cascade="all, delete-orphan")


class CVDocument(Base):
    __tablename__ = 'cv_documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'))
    version_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    metadata_json = Column('metadata', JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="cvs")
    applications = relationship("Application", back_populates="cv")

class UserSession(Base):
    __tablename__ = 'user_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('user_profiles.id'))
    platform = Column(String, nullable=False)
    encrypted_session_path = Column(String, nullable=False)
    last_verified = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="sessions")
