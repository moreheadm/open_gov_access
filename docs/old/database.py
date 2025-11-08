"""
Database models for supervisor voting records
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, 
    Text, Boolean, ForeignKey, JSON, Date, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum


Base = declarative_base()


class VoteType(enum.Enum):
    """Vote types"""
    AYE = "aye"
    NO = "no"
    ABSTAIN = "abstain"
    ABSENT = "absent"
    EXCUSED = "excused"


class Meeting(Base):
    """Board of Supervisors meeting"""
    __tablename__ = 'meetings'
    
    id = Column(Integer, primary_key=True)
    meeting_date = Column(Date, nullable=False, unique=True, index=True)
    meeting_type = Column(String(100))  # "Regular", "Special", etc.
    
    # Relationships
    documents = relationship("Document", back_populates="meeting")
    items = relationship("Item", back_populates="meeting")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Document(Base):
    """Source document (agenda, minutes, etc.)"""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    doc_id = Column(String(50), unique=True, nullable=False, index=True)
    source = Column(String(100), nullable=False)
    doc_type = Column(String(50), nullable=False)  # "agenda", "minutes"
    url = Column(Text, nullable=False)
    
    meeting_id = Column(Integer, ForeignKey('meetings.id'))
    meeting = relationship("Meeting", back_populates="documents")
    
    # Content
    raw_content = Column(Text)  # Original content
    markdown_content = Column(Text)  # Converted to markdown
    
    # Metadata
    doc_metadata = Column(JSON)
    scraped_at = Column(DateTime, nullable=False)
    processed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.now)


class Supervisor(Base):
    """SF Board of Supervisors member"""
    __tablename__ = 'supervisors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    district = Column(Integer, nullable=False)
    
    # Time in office
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    votes = relationship("Vote", back_populates="supervisor")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Supervisor {self.name} (District {self.district})>"


class Item(Base):
    """Agenda/voting item"""
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True)
    
    # Meeting info
    meeting_id = Column(Integer, ForeignKey('meetings.id'))
    meeting = relationship("Meeting", back_populates="items")
    
    # Item details
    file_number = Column(String(50), index=True)  # e.g., "250210"
    title = Column(Text, nullable=False)
    description = Column(Text)
    item_type = Column(String(100))  # "Ordinance", "Resolution", etc.
    
    # Sponsor/author
    sponsor = Column(String(200))
    
    # Vote results
    result = Column(String(50))  # "APPROVED", "REJECTED", "CONTINUED", etc.
    vote_count_aye = Column(Integer)
    vote_count_no = Column(Integer)
    vote_count_abstain = Column(Integer)
    vote_count_absent = Column(Integer)
    
    # Relationships
    votes = relationship("Vote", back_populates="item")
    
    # Metadata
    item_metadata = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<Item {self.file_number}: {self.title[:50]}>"


class Vote(Base):
    """Individual supervisor vote on an item"""
    __tablename__ = 'votes'
    
    id = Column(Integer, primary_key=True)
    
    # References
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    item = relationship("Item", back_populates="votes")
    
    supervisor_id = Column(Integer, ForeignKey('supervisors.id'), nullable=False)
    supervisor = relationship("Supervisor", back_populates="votes")
    
    # Vote
    vote = Column(SQLEnum(VoteType), nullable=False)
    
    # Context
    notes = Column(Text)  # Any additional notes about the vote
    
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Vote {self.supervisor.name}: {self.vote.value} on {self.item.file_number}>"


# Database management functions
def init_db(database_url: str = "sqlite:///data/supervisor_votes.db"):
    """Initialize database and create tables"""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()


def seed_supervisors(session):
    """
    Seed database with current SF Board of Supervisors
    Source: https://sfbos.org/supervisors (as of 2025)
    """
    supervisors = [
        {"name": "Connie Chan", "district": 1, "is_active": True},
        {"name": "Catherine Stefani", "district": 2, "is_active": True},
        {"name": "Aaron Peskin", "district": 3, "is_active": True},
        {"name": "Joel Engardio", "district": 4, "is_active": True},
        {"name": "Dean Preston", "district": 5, "is_active": True},
        {"name": "Matt Dorsey", "district": 6, "is_active": True},
        {"name": "Myrna Melgar", "district": 7, "is_active": True},
        {"name": "Rafael Mandelman", "district": 8, "is_active": True},
        {"name": "Hillary Ronen", "district": 9, "is_active": True},
        {"name": "Shamann Walton", "district": 10, "is_active": True},
        {"name": "Ahsha Safai", "district": 11, "is_active": True},
    ]
    
    for sup_data in supervisors:
        # Check if already exists
        existing = session.query(Supervisor).filter_by(
            name=sup_data["name"],
            district=sup_data["district"]
        ).first()
        
        if not existing:
            supervisor = Supervisor(**sup_data)
            session.add(supervisor)
    
    session.commit()
    print(f"✓ Seeded {len(supervisors)} supervisors")
