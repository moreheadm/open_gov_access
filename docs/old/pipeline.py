"""
ETL Pipeline: Extract voting data from documents and load into database
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import pdfplumber
from io import BytesIO

import sys
sys.path.append('..')
from models.database import (
    Meeting, Document, Item, Vote, Supervisor, VoteType,
    get_session
)


class VoteParser:
    """Parse voting records from board minutes"""
    
    # Supervisor names to match
    SUPERVISOR_NAMES = [
        "Chan", "Stefani", "Peskin", "Engardio", "Preston",
        "Dorsey", "Melgar", "Mandelman", "Ronen", "Walton", "Safai"
    ]
    
    # Vote patterns
    VOTE_PATTERNS = {
        VoteType.AYE: r'\b(aye|yes)\b',
        VoteType.NO: r'\b(no|nay)\b',
        VoteType.ABSTAIN: r'\b(abstain)\b',
        VoteType.ABSENT: r'\b(absent)\b',
        VoteType.EXCUSED: r'\b(excused)\b',
    }
    
    @classmethod
    def pdf_to_text(cls, pdf_bytes: bytes) -> str:
        """Convert PDF bytes to text"""
        text_parts = []
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    @classmethod
    def pdf_to_markdown(cls, pdf_bytes: bytes) -> str:
        """Convert PDF to markdown format"""
        text = cls.pdf_to_text(pdf_bytes)
        
        # Basic markdown conversion
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Detect headings (all caps, short lines)
            if line.isupper() and len(line) < 100:
                lines.append(f"## {line}")
            else:
                lines.append(line)
        
        return "\n\n".join(lines)
    
    @classmethod
    def extract_items(cls, text: str) -> List[Dict[str, Any]]:
        """
        Extract voting items from minutes text
        
        Returns list of items with:
        - file_number
        - title
        - description
        - result
        - vote_counts
        """
        items = []
        
        # Pattern: File No. 250210 - Title
        # Followed by vote information
        file_pattern = r'File\s+No\.\s+(\d+)\s*[-–]\s*([^\n]+)'
        
        matches = list(re.finditer(file_pattern, text, re.IGNORECASE))
        
        for i, match in enumerate(matches):
            file_number = match.group(1)
            title = match.group(2).strip()
            
            # Get text until next file or end
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            item_text = text[start:end]
            
            # Extract vote result
            result = cls._extract_result(item_text)
            
            # Extract vote counts
            vote_counts = cls._extract_vote_counts(item_text)
            
            # Extract individual votes
            individual_votes = cls._extract_individual_votes(item_text)
            
            items.append({
                'file_number': file_number,
                'title': title,
                'description': item_text[:500],  # First 500 chars
                'result': result,
                'vote_counts': vote_counts,
                'individual_votes': individual_votes
            })
        
        return items
    
    @classmethod
    def _extract_result(cls, text: str) -> Optional[str]:
        """Extract vote result (APPROVED, REJECTED, etc.)"""
        result_patterns = [
            r'\b(APPROVED|PASSED|ADOPTED)\b',
            r'\b(REJECTED|FAILED)\b',
            r'\b(CONTINUED|DEFERRED)\b',
        ]
        
        for pattern in result_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    @classmethod
    def _extract_vote_counts(cls, text: str) -> Dict[str, int]:
        """Extract vote counts (e.g., '8 ayes, 3 noes')"""
        counts = {
            'aye': 0,
            'no': 0,
            'abstain': 0,
            'absent': 0
        }
        
        # Pattern: "8 ayes, 3 noes"
        for vote_type in ['aye', 'no', 'abstain', 'absent']:
            pattern = rf'(\d+)\s+{vote_type}s?'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                counts[vote_type] = int(match.group(1))
        
        return counts
    
    @classmethod
    def _extract_individual_votes(cls, text: str) -> List[Dict[str, str]]:
        """
        Extract individual supervisor votes
        
        Returns list of {'supervisor': name, 'vote': vote_type}
        """
        votes = []
        
        # Look for voting patterns
        # "Supervisor Preston voted aye"
        # "Vote: Ayes - Chan, Peskin, Preston; Noes - Dorsey"
        
        # Try pattern 1: Individual votes
        for supervisor in cls.SUPERVISOR_NAMES:
            for vote_type, pattern in cls.VOTE_PATTERNS.items():
                # Look for "Supervisor X voted Y" or "X - Y"
                vote_pattern = rf'\b{supervisor}\b.*?\b({pattern})\b'
                if re.search(vote_pattern, text, re.IGNORECASE):
                    votes.append({
                        'supervisor': supervisor,
                        'vote': vote_type.value
                    })
                    break
        
        # Try pattern 2: Roll call format
        # "Ayes: Chan, Peskin, Preston..."
        for vote_type in ['aye', 'no', 'abstain', 'absent']:
            pattern = rf'{vote_type}s?:\s*([^\n;]+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                names_text = match.group(1)
                for supervisor in cls.SUPERVISOR_NAMES:
                    if supervisor in names_text:
                        # Check if not already added
                        if not any(v['supervisor'] == supervisor for v in votes):
                            votes.append({
                                'supervisor': supervisor,
                                'vote': vote_type
                            })
        
        return votes


class ETLPipeline:
    """ETL pipeline to process scraped documents"""
    
    def __init__(self, engine):
        self.engine = engine
        self.session = get_session(engine)
    
    def process_document(self, scraped_doc) -> Document:
        """
        Process a scraped document:
        1. Convert to markdown
        2. Extract voting data
        3. Load into database
        
        Args:
            scraped_doc: ScrapedDocument from scraper
            
        Returns:
            Document database object
        """
        print(f"Processing {scraped_doc.doc_type} from {scraped_doc.date.date()}...")
        
        # Check if document already processed
        existing = self.session.query(Document).filter_by(
            doc_id=scraped_doc.doc_id
        ).first()
        
        if existing and existing.processed_at:
            print(f"  Already processed")
            return existing
        
        # Get or create meeting
        meeting = self._get_or_create_meeting(scraped_doc.date.date())
        
        # Convert PDF to text and markdown
        print(f"  Converting to markdown...")
        text = VoteParser.pdf_to_text(scraped_doc.raw_content)
        markdown = VoteParser.pdf_to_markdown(scraped_doc.raw_content)
        
        # Create or update document
        if existing:
            doc = existing
        else:
            doc = Document(
                doc_id=scraped_doc.doc_id,
                source=scraped_doc.source,
                doc_type=scraped_doc.doc_type,
                url=scraped_doc.url,
                meeting_id=meeting.id,
                scraped_at=scraped_doc.scraped_at
            )
            self.session.add(doc)
        
        doc.raw_content = text
        doc.markdown_content = markdown
        doc.doc_metadata = scraped_doc.metadata
        doc.processed_at = datetime.now()
        
        # Extract and load voting data (only for minutes)
        if scraped_doc.doc_type == 'minutes':
            print(f"  Extracting votes...")
            items = VoteParser.extract_items(text)
            print(f"  Found {len(items)} items")
            
            for item_data in items:
                self._process_item(meeting, item_data)
        
        self.session.commit()
        print(f"  ✓ Processed")
        
        return doc
    
    def _get_or_create_meeting(self, meeting_date) -> Meeting:
        """Get or create meeting record"""
        meeting = self.session.query(Meeting).filter_by(
            meeting_date=meeting_date
        ).first()
        
        if not meeting:
            meeting = Meeting(
                meeting_date=meeting_date,
                meeting_type="Regular"
            )
            self.session.add(meeting)
            self.session.flush()
        
        return meeting
    
    def _process_item(self, meeting: Meeting, item_data: Dict[str, Any]):
        """Process a voting item"""
        # Check if item already exists
        existing = self.session.query(Item).filter_by(
            meeting_id=meeting.id,
            file_number=item_data['file_number']
        ).first()
        
        if existing:
            return  # Already processed
        
        # Create item
        item = Item(
            meeting_id=meeting.id,
            file_number=item_data['file_number'],
            title=item_data['title'],
            description=item_data.get('description'),
            result=item_data.get('result'),
            vote_count_aye=item_data['vote_counts'].get('aye', 0),
            vote_count_no=item_data['vote_counts'].get('no', 0),
            vote_count_abstain=item_data['vote_counts'].get('abstain', 0),
            vote_count_absent=item_data['vote_counts'].get('absent', 0)
        )
        self.session.add(item)
        self.session.flush()
        
        # Add individual votes
        for vote_data in item_data.get('individual_votes', []):
            self._add_vote(item, vote_data)
    
    def _add_vote(self, item: Item, vote_data: Dict[str, str]):
        """Add individual supervisor vote"""
        # Find supervisor by name
        supervisor = self.session.query(Supervisor).filter(
            Supervisor.name.contains(vote_data['supervisor'])
        ).first()
        
        if not supervisor:
            print(f"    Warning: Supervisor not found: {vote_data['supervisor']}")
            return
        
        # Create vote
        vote = Vote(
            item_id=item.id,
            supervisor_id=supervisor.id,
            vote=VoteType(vote_data['vote'])
        )
        self.session.add(vote)
    
    def close(self):
        """Close database session"""
        self.session.close()
