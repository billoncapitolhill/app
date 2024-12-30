from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from .base import BaseModel

class AISummary(BaseModel):
    """Model for AI-generated summaries."""
    __tablename__ = 'ai_summaries'

    target_id = Column(UUID(as_uuid=True), nullable=False)
    target_type = Column(String(20), nullable=False)  # 'bill' or 'amendment'
    summary = Column(Text, nullable=False)
    perspective = Column(String(100), nullable=False)
    key_points = Column(JSONB)
    estimated_cost_impact = Column(Text)
    government_growth_analysis = Column(Text)
    market_impact_analysis = Column(Text)
    liberty_impact_analysis = Column(Text)

    # Polymorphic relationships
    bill = relationship("Bill", back_populates="ai_summary",
                       primaryjoin="and_(AISummary.target_id==Bill.id, "
                                 "AISummary.target_type=='bill')")
    amendment = relationship("Amendment", back_populates="ai_summary",
                           primaryjoin="and_(AISummary.target_id==Amendment.id, "
                                     "AISummary.target_type=='amendment')")

class ProcessingStatus(BaseModel):
    """Model for tracking processing status of bills and amendments."""
    __tablename__ = 'processing_status'

    target_id = Column(UUID(as_uuid=True), nullable=False)
    target_type = Column(String(20), nullable=False)  # 'bill' or 'amendment'
    last_checked = Column(DateTime)
    last_processed = Column(DateTime)
    status = Column(String(20), nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text) 