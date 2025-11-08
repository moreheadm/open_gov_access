"""
SF Board of Supervisors Meeting Scraper
Extends BaseDataSourceScraper for SF BOS meetings
"""

import requests
from bs4 import BeautifulSoup
import re
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin
import time

try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call(["pip", "install", "pdfplumber", "--break-system-packages"])
    import pdfplumber

from base_scraper import BaseDataSourceScraper, Document


class SFBOSScraper(BaseDataSourceScraper):
    """Scraper for SF Board of Supervisors meeting documents"""
    
    BASE_URL = "https://sfbos.org"
    MEETINGS_URL = "https://sfbos.org/meetings/full-board-meetings"
    
    def __init__(self, output_dir: str = "data/sfbos_meetings"):
        super().__init__(output_dir, "SF Board of Supervisors")
        
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; CivicDataBot/1.0)'
        })
    
    def discover_documents(self) -> List[Document]:
        """Discover available meeting documents"""
        documents = []
        
        try:
            # Fetch the meetings page
            print(f"  Fetching: {self.MEETINGS_URL}")
            response = self.session.get(self.MEETINGS_URL, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links
            all_links = soup.find_all('a', href=True)
            
            # Parse meetings
            meetings = self._parse_meetings(soup, all_links)
            
            # Create Document objects
            for meeting in meetings:
                if meeting.get('agenda'):
                    doc_id = Document.generate_id(meeting['agenda'], 'agenda', meeting['date'])
                    doc = Document(
                        doc_id=doc_id,
                        doc_type='agenda',
                        url=meeting['agenda'],
                        date=meeting['date'],
                        metadata={
                            'meeting_date': meeting['date'],
                            'source': 'SF Board of Supervisors'
                        }
                    )
                    documents.append(doc)
                
                if meeting.get('minutes'):
                    doc_id = Document.generate_id(meeting['minutes'], 'minutes', meeting['date'])
                    doc = Document(
                        doc_id=doc_id,
                        doc_type='minutes',
                        url=meeting['minutes'],
                        date=meeting['date'],
                        metadata={
                            'meeting_date': meeting['date'],
                            'source': 'SF Board of Supervisors'
                        }
                    )
                    documents.append(doc)
            
        except Exception as e:
            print(f"  ✗ Error discovering documents: {e}")
        
        return documents
    
    def _parse_meetings(self, soup: BeautifulSoup, all_links: List) -> List[Dict]:
        """Parse meeting information from the page"""
        meetings = []
        seen_dates = set()
        
        # Strategy 1: Look for date patterns and nearby links
        text_content = soup.get_text()
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        current_date = None
        for line in lines:
            # Look for date patterns (e.g., "Tuesday, October 28, 2025")
            date_match = re.search(
                r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})',
                line
            )
            if date_match:
                current_date = date_match.group(1)
        
        # Strategy 2: Parse all links and associate with dates
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            
            # Skip if not a document link
            if 'agenda' not in href.lower() and 'minutes' not in href.lower():
                continue
            
            # Try to extract date from URL or surrounding context
            # URL patterns: /meeting/agenda/2025/bag102825_agenda
            date_from_url = self._extract_date_from_url(href)
            if not date_from_url:
                continue
            
            # Create or update meeting entry
            meeting = next((m for m in meetings if m['date'] == date_from_url), None)
            if not meeting:
                if date_from_url in seen_dates:
                    continue  # Skip duplicates
                seen_dates.add(date_from_url)
                meeting = {
                    'date': date_from_url,
                    'agenda': None,
                    'minutes': None
                }
                meetings.append(meeting)
            
            # Determine document type and add URL
            full_url = urljoin(self.BASE_URL, href)
            if 'agenda' in href.lower():
                meeting['agenda'] = full_url
            elif 'minutes' in href.lower():
                meeting['minutes'] = full_url
        
        # Sort by date (most recent first)
        meetings.sort(
            key=lambda m: self._date_to_sortable(m['date']),
            reverse=True
        )
        
        return meetings
    
    def _extract_date_from_url(self, url: str) -> Optional[str]:
        """
        Extract date from URL pattern
        Example: /meeting/agenda/2025/bag102825_agenda -> "October 28, 2025"
        """
        # Pattern: bag102825 = bag + MM + DD + YY
        match = re.search(r'bag(\d{2})(\d{2})(\d{2})', url)
        if match:
            month, day, year = match.groups()
            year = f"20{year}"
            
            # Convert month number to name
            month_names = [
                '', 'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            month_name = month_names[int(month)]
            
            # Format: "October 28, 2025"
            return f"{month_name} {int(day)}, {year}"
        
        return None
    
    def _date_to_sortable(self, date_str: str) -> str:
        """
        Convert date string to sortable format
        "October 28, 2025" -> "2025-10-28"
        """
        try:
            from datetime import datetime
            parsed = datetime.strptime(date_str, "%B %d, %Y")
            return parsed.strftime("%Y-%m-%d")
        except:
            return date_str
    
    def download_document(self, doc: Document) -> bool:
        """Download a PDF document"""
        try:
            # Create safe filename
            safe_date = doc.date.replace(", ", "-").replace(" ", "-")
            filename = f"{safe_date}_{doc.doc_type}.pdf"
            output_path = self.raw_dir / filename
            
            # Skip if already exists
            if output_path.exists():
                doc.original_path = output_path
                return True
            
            # Download
            print(f"    Downloading: {doc.url}")
            response = self.session.get(doc.url, timeout=30)
            response.raise_for_status()
            
            # Save
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            doc.original_path = output_path
            time.sleep(1)  # Be polite to the server
            return True
            
        except Exception as e:
            print(f"    ✗ Download error: {e}")
            return False
    
    def extract_text(self, doc: Document) -> str:
        """Extract text from PDF using pdfplumber"""
        if not doc.original_path or not doc.original_path.exists():
            return ""
        
        try:
            text_parts = []
            
            with pdfplumber.open(doc.original_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}\n")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"    ✗ Text extraction error: {e}")
            return ""


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scrape SF Board of Supervisors meeting documents'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of meetings to scrape (default: all)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-scrape of existing documents'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset scraper state (clear all history)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/sfbos_meetings',
        help='Output directory (default: data/sfbos_meetings)'
    )
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = SFBOSScraper(output_dir=args.output)
    
    # Reset state if requested
    if args.reset:
        scraper.reset_state()
        return
    
    # Run scraper
    documents = scraper.scrape(limit=args.limit, force=args.force)
    
    # Print results
    print(f"\n✓ Successfully processed {len(documents)} documents")


if __name__ == "__main__":
    main()
