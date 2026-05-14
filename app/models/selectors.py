from sqlalchemy import Column, String, Integer, Float, DateTime
from datetime import datetime
from .base import Base

class SelectorIntelligence(Base):
    """
    Persists successful selector fallbacks so the bot learns over time.
    """
    __tablename__ = 'selector_intelligence'

    platform = Column(String, primary_key=True) # e.g., 'greenhouse'
    field_name = Column(String, primary_key=True) # e.g., 'first_name'
    successful_selector = Column(String, nullable=False)
    success_count = Column(Integer, default=1)
    last_success_at = Column(DateTime, default=datetime.utcnow)
