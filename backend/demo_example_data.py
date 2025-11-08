#!/usr/bin/env python3
"""
Demonstration script to show example data loaded into the database.
This script initializes a SQLite database with example data and displays it.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import (
    init_db, get_session, seed_officials, seed_example_data,
    Official, Legislation, Meeting, Action, ActionType, VoteType, OfficialType
)
from sqlalchemy import func


def display_example_data():
    """Display the example data loaded into the database"""
    
    # Initialize database (SQLite in-memory for demo)
    print("=" * 80)
    print("SF Board of Supervisors - Example Data Demonstration")
    print("=" * 80)
    print()
    
    print("Initializing database...")
    engine = init_db("sqlite:///:memory:")
    session = get_session(engine)
    
    # Seed data
    print("Seeding officials...")
    seed_officials(session)
    
    print("Seeding example legislation...")
    seed_example_data(session)
    print()
    
    # Display the data
    print("=" * 80)
    print("LEGISLATION DETAILS")
    print("=" * 80)
    
    legislation = session.query(Legislation).filter_by(file_number="250804").first()
    if legislation:
        print(f"File Number: {legislation.file_number}")
        print(f"Type: {legislation.legislation_type}")
        print(f"Status: {legislation.status.value}")
        print(f"Category: {legislation.category}")
        print()
        print(f"Title: {legislation.title}")
        print()
        print(f"Description:")
        print(f"  {legislation.description[:200]}...")
        print()
        print(f"URL: {legislation.url}")
        print()
        
        if legislation.extra_data:
            print("Additional Data:")
            for key, value in legislation.extra_data.items():
                if isinstance(value, list):
                    print(f"  {key}: {len(value)} items")
                else:
                    print(f"  {key}: {value}")
        print()
    
    # Display sponsors
    print("=" * 80)
    print("SPONSORS")
    print("=" * 80)
    
    sponsor_actions = session.query(Action).filter(
        Action.legislation_id == legislation.id,
        Action.action_type.in_([ActionType.SPONSOR, ActionType.CO_SPONSOR])
    ).all()
    
    for action in sponsor_actions:
        official = session.query(Official).filter_by(id=action.official_id).first()
        print(f"  {action.action_type.value.replace('_', ' ').title()}: {official.name}")
    print()
    
    # Display meetings
    print("=" * 80)
    print("LEGISLATIVE HISTORY")
    print("=" * 80)
    
    meetings = session.query(Meeting).order_by(Meeting.meeting_date).all()
    for meeting in meetings:
        print(f"  {meeting.meeting_date.strftime('%Y-%m-%d')} - {meeting.meeting_type.value.title()} Meeting")
    print()
    
    # Display votes
    print("=" * 80)
    print("VOTING RECORD (Final Passage - 2025-10-21)")
    print("=" * 80)
    
    final_meeting = session.query(Meeting).filter(
        Meeting.meeting_date >= "2025-10-21"
    ).order_by(Meeting.meeting_date).first()
    
    if final_meeting:
        vote_actions = session.query(Action).filter(
            Action.legislation_id == legislation.id,
            Action.meeting_id == final_meeting.id,
            Action.action_type == ActionType.VOTE
        ).all()
        
        # Count votes
        vote_counts = {
            VoteType.AYE: 0,
            VoteType.NO: 0,
            VoteType.ABSTAIN: 0,
            VoteType.ABSENT: 0,
            VoteType.EXCUSED: 0
        }
        
        print()
        for action in vote_actions:
            official = session.query(Official).filter_by(id=action.official_id).first()
            vote_str = action.vote.value.upper()
            print(f"  {official.name:25} (District {official.district or 'N/A':2}) - {vote_str}")
            vote_counts[action.vote] += 1
        
        print()
        print("-" * 80)
        print("Vote Summary:")
        print(f"  AYE:     {vote_counts[VoteType.AYE]}")
        print(f"  NO:      {vote_counts[VoteType.NO]}")
        print(f"  ABSTAIN: {vote_counts[VoteType.ABSTAIN]}")
        print(f"  ABSENT:  {vote_counts[VoteType.ABSENT]}")
        print(f"  EXCUSED: {vote_counts[VoteType.EXCUSED]}")
        print()

        # Calculate result
        total_votes = vote_counts[VoteType.AYE] + vote_counts[VoteType.NO]
        if total_votes > 0:
            aye_percentage = (vote_counts[VoteType.AYE] / total_votes) * 100
            print(f"Result: {vote_counts[VoteType.AYE]}/{total_votes} ({aye_percentage:.1f}%) - PASSED")
        print()
    
    # Display statistics
    print("=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    
    print(f"  Officials:    {session.query(func.count(Official.id)).scalar()}")
    print(f"  Legislation:  {session.query(func.count(Legislation.id)).scalar()}")
    print(f"  Meetings:     {session.query(func.count(Meeting.id)).scalar()}")
    print(f"  Actions:      {session.query(func.count(Action.id)).scalar()}")
    print()
    
    session.close()
    
    print("=" * 80)
    print("Demo complete!")
    print()
    print("To load this example data into your database, run:")
    print("  python main.py init --with-examples")
    print("=" * 80)


if __name__ == "__main__":
    display_example_data()

