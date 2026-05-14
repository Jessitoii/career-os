from sqlalchemy import Column, String, Integer
from .base import Base

class PlatformRateLimit(Base):
    __tablename__ = 'platform_rate_limits'

    platform = Column(String, primary_key=True)
    min_wait_seconds = Column(Integer, default=120)
    max_wait_seconds = Column(Integer, default=600)
    daily_cap = Column(Integer, default=20)
    notes = Column(String)
