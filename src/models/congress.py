from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel

class Bill(BaseModel):
    """Model for congressional bills."""
    __tablename__ = 'bills'

    congress_number = Column(Integer, nullable=False)
    bill_type = Column(String(10), nullable=False)
    bill_number = Column(Integer, nullable=False)
    title = Column(Text)
    description = Column(Text)
    origin_chamber = Column(String(10))
    origin_chamber_code = Column(String(1))
    introduced_date = Column(DateTime)
    latest_action_date = Column(DateTime)
    latest_action_text = Column(Text)
    update_date = Column(DateTime)
    constitutional_authority_text = Column(Text)
    url = Column(String(500))

    # Relationships
    amendments = relationship("Amendment", back_populates="bill")
    ai_summary = relationship("AISummary", back_populates="bill",
                            primaryjoin="and_(Bill.id==AISummary.target_id, "
                                      "AISummary.target_type=='bill')")

class Amendment(BaseModel):
    """Model for bill amendments."""
    __tablename__ = 'amendments'

    bill_id = Column(UUID(as_uuid=True), ForeignKey('bills.id'), nullable=False)
    congress_number = Column(Integer, nullable=False)
    amendment_type = Column(String(10), nullable=False)
    amendment_number = Column(Integer, nullable=False)
    description = Column(Text)
    purpose = Column(Text)
    submitted_date = Column(DateTime)
    latest_action_date = Column(DateTime)
    latest_action_text = Column(Text)
    chamber = Column(String(10))
    url = Column(String(500))

    # Relationships
    bill = relationship("Bill", back_populates="amendments")
    ai_summary = relationship("AISummary", back_populates="amendment",
                            primaryjoin="and_(Amendment.id==AISummary.target_id, "
                                      "AISummary.target_type=='amendment')") 