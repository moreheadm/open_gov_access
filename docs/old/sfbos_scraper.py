"""
SF Board of Supervisors Meeting Scraper
Scrapes agendas and minutes from sfbos.org and converts PDFs to text
"""

import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin
import time

# For PDF processing
try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call(["pip", "install", "pdfplumber", "--break-system-packages"])
    import pdfplumber


class MeetingDocument:
    """Represents a meeting document (agenda or minutes)"""
    def __init__(self, doc_type: str, url: str, meeting_date: str):
        self.doc_type = doc_type  # "agenda" or "minutes"
        self.url = url
        self.meeting_date = meeting_date
        self.original_path: Optional[Path] = None
        self.text_path: Optional[Path] = None
        self.text_content: Optional[str] = None
        
    def to_dict(self) -> Dict:
        return {
            "doc_type": self.doc_type,
            "url": self.url,
            "meeting_date": self.meeting_date,
            "original_path": str(self.original_path) if self.original_path else None,
            "text_path": str(self.text_path) if self.text_path else None,
            "scraped_at": datetime.now().isoformat()
        }


class SFBOSScraper:
    """Scraper for SF Board of Supervisors meeting documents"""
    
    BASE_URL = "https://sfbos.org"
    MEETINGS_URL = "https://sfbos.org/meetings/full-board-meetings"
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.raw_dir = self.output_dir / "raw"
        self.text_dir = self.output_dir / "text"
        self.metadata_dir = self.output_dir / "metadata"
        
        for d in [self.raw_dir, self.text_dir, self.metadata_dir]:
            d.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; CivicDataBot/1.0)'
        })
    
    def fetch_meetings_page(self) -> BeautifulSoup:
        """Fetch the main meetings listing page"""
        print(f"Fetching meetings page: {self.MEETINGS_URL}")
        response = self.session.get(self.MEETINGS_URL)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    
    def extract_meeting_links(self, soup: BeautifulSoup, limit: Optional[int] = None) -> List[Dict]:
        """Extract meeting information from the page"""
        meetings = []
        
        # Parse the text content to find meeting entries
        # Format: "Date | Agenda | Minutes | Video"
        text_content = soup.get_text()
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for date patterns (e.g., "Tuesday, October 28, 2025")
            date_match = re.search(r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})', line)
            
            if date_match:
                meeting_date = date_match.group(1)
                
                # Find agenda and minutes links in nearby lines
                agenda_link = None
                minutes_link = None
                
                # Look at the next few lines for Agenda/Minutes
                for j in range(i, min(i + 5, len(lines))):
                    links = soup.find_all('a', string=re.compile(r'Agenda|Minutes', re.I))
                    
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text().lower()
                        full_url = urljoin(self.BASE_URL, href)
                        
                        if 'agenda' in text:
                            agenda_link = full_url
                        elif 'minute' in text:
                            minutes_link = full_url
                
                if agenda_link or minutes_link:
                    meetings.append({
                        'date': meeting_date,
                        'agenda': agenda_link,
                        'minutes': minutes_link
                    })
                    
                    if limit and len(meetings) >= limit:
                        break
            
            i += 1
        
        # Alternative parsing: find all links with Agenda/Minutes
        if not meetings:
            all_links = soup.find_all('a', href=True)
            current_date = None
            
            for link in all_links:
                text = link.get_text().strip()
                href = link.get('href', '')
                
                # Check if this is a date line
                date_match = re.search(r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})', text)
                if date_match:
                    current_date = date_match.group(1)
                
                # Check if this is an agenda or minutes link
                if current_date and ('agenda' in href.lower() or 'minutes' in href.lower()):
                    full_url = urljoin(self.BASE_URL, href)
                    
                    # Find or create meeting entry
                    meeting = next((m for m in meetings if m['date'] == current_date), None)
                    if not meeting:
                        meeting = {'date': current_date, 'agenda': None, 'minutes': None}
                        meetings.append(meeting)
                    
                    if 'agenda' in href.lower():
                        meeting['agenda'] = full_url
                    elif 'minutes' in href.lower():
                        meeting['minutes'] = full_url
                    
                    if limit and len(meetings) >= limit:
                        break
        
        return meetings
    
    def download_pdf(self, url: str, output_path: Path) -> bool:
        """Download a PDF file"""
        try:
            print(f"  Downloading: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"  Saved to: {output_path}")
            return True
        except Exception as e:
            print(f"  Error downloading {url}: {e}")
            return False
    
    def pdf_to_text(self, pdf_path: Path) -> str:
        """Convert PDF to text using pdfplumber"""
        try:
            print(f"  Converting PDF to text: {pdf_path.name}")
            text_parts = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}\n")
            
            return "\n".join(text_parts)
        except Exception as e:
            print(f"  Error converting PDF to text: {e}")
            return f"[Error extracting text: {e}]"
    
    def process_document(self, doc_type: str, url: str, meeting_date: str) -> MeetingDocument:
        """Download and process a single document"""
        doc = MeetingDocument(doc_type, url, meeting_date)
        
        # Create safe filename
        safe_date = meeting_date.replace('/', '-')
        filename = f"{safe_date}_{doc_type}.pdf"
        
        # Download PDF
        pdf_path = self.raw_dir / filename
        if self.download_pdf(url, pdf_path):
            doc.original_path = pdf_path
            
            # Convert to text
            text_content = self.pdf_to_text(pdf_path)
            doc.text_content = text_content
            
            # Save text file
            text_path = self.text_dir / f"{safe_date}_{doc_type}.txt"
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            doc.text_path = text_path
            
            # Save metadata
            metadata_path = self.metadata_dir / f"{safe_date}_{doc_type}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(doc.to_dict(), f, indent=2)
        
        return doc
    
    def scrape(self, limit: Optional[int] = None) -> List[MeetingDocument]:
        """Main scraping method"""
        print("=" * 60)
        print("SF Board of Supervisors Meeting Scraper")
        print("=" * 60)
        
        # Fetch meetings page
        soup = self.fetch_meetings_page()
        
        # Extract meeting links
        meetings = self.extract_meeting_links(soup, limit=limit)
        print(f"\nFound {len(meetings)} meetings")
        
        # Process each meeting
        all_documents = []
        
        for i, meeting in enumerate(meetings, 1):
            print(f"\n[{i}/{len(meetings)}] Processing meeting: {meeting['date']}")
            
            if meeting['agenda']:
                doc = self.process_document('agenda', meeting['agenda'], meeting['date'])
                all_documents.append(doc)
                time.sleep(1)  # Be polite
            
            if meeting['minutes']:
                doc = self.process_document('minutes', meeting['minutes'], meeting['date'])
                all_documents.append(doc)
                time.sleep(1)  # Be polite
        
        print("\n" + "=" * 60)
        print(f"Scraping complete! Processed {len(all_documents)} documents")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("=" * 60)
        
        return all_documents


def main():
    """Main entry point"""
    scraper = SFBOSScraper(output_dir="data/sfbos_meetings")
    
    # Start with just 5 most recent meetings for testing
    documents = scraper.scrape(limit=5)
    
    # Print summary
    print("\nSummary:")
    for doc in documents:
        status = "✓" if doc.text_content else "✗"
        print(f"{status} {doc.meeting_date} - {doc.doc_type}")


if __name__ == "__main__":
    main()
