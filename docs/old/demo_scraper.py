"""
Demo script to generate sample output showing what the scraper produces
This simulates the output structure without actually scraping (for demo purposes)
"""

from pathlib import Path
import json
from datetime import datetime

def create_demo_output():
    """Create sample output to demonstrate the scraper's results"""
    
    # Create output directories
    base_dir = Path("data/sfbos_meetings_demo")
    raw_dir = base_dir / "raw"
    text_dir = base_dir / "text"
    metadata_dir = base_dir / "metadata"
    
    for d in [raw_dir, text_dir, metadata_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # Sample meeting data
    meetings = [
        {
            "date": "October 28, 2025",
            "agenda_url": "https://sfbos.org/meeting/agenda/2025/bag102825_agenda",
            "minutes_url": None
        },
        {
            "date": "October 21, 2025",
            "agenda_url": "https://sfbos.org/meeting/agenda/2025/bag102125_agenda",
            "minutes_url": "https://sfbos.org/meeting/minutes/2025/bag102125_minutes"
        },
        {
            "date": "October 7, 2025",
            "agenda_url": "https://sfbos.org/meeting/2025/agenda/bag100725_agenda",
            "minutes_url": "https://sfbos.org/meeting/minutes/2025/bag100725_minutes"
        }
    ]
    
    # Generate sample documents
    for i, meeting in enumerate(meetings, 1):
        date_safe = meeting["date"].replace(", ", "-").replace(" ", "-")
        
        # Generate sample agenda
        if meeting["agenda_url"]:
            agenda_text = f"""--- Page 1 ---
SAN FRANCISCO BOARD OF SUPERVISORS
LEGISLATIVE RESEARCH CENTER

{meeting["date"]}
BOARD OF SUPERVISORS MEETING AGENDA

BOARD OF SUPERVISORS OF THE CITY AND COUNTY OF SAN FRANCISCO

Room 250, City Hall
1 Dr. Carlton B. Goodlett Place
San Francisco, CA 94102-4689

REGULAR MEETING - 2:00 PM

--- Page 2 ---

ROLL CALL AND PLEDGE OF ALLEGIANCE

COMMUNICATIONS

APPROVAL OF MINUTES
Minutes from previous Board meeting

CONSENT CALENDAR
• File No. 250{i}01 - Resolution authorizing budget allocation
• File No. 250{i}02 - Ordinance amending zoning regulations
• File No. 250{i}03 - Lease agreement for city property

--- Page 3 ---

REGULAR AGENDA

• File No. 250{i}10 - Hearing on affordable housing development at 1234 Mission Street
• File No. 250{i}11 - Budget and Finance Committee report
• File No. 250{i}12 - Public safety funding allocation

ADJOURNMENT
"""
            
            # Save text file
            text_path = text_dir / f"{date_safe}_agenda.txt"
            with open(text_path, 'w') as f:
                f.write(agenda_text)
            
            # Save metadata
            metadata = {
                "doc_type": "agenda",
                "url": meeting["agenda_url"],
                "meeting_date": meeting["date"],
                "original_path": f"data/sfbos_meetings_demo/raw/{date_safe}_agenda.pdf",
                "text_path": str(text_path),
                "scraped_at": datetime.now().isoformat()
            }
            
            metadata_path = metadata_dir / f"{date_safe}_agenda.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✓ Generated {date_safe}_agenda.txt")
        
        # Generate sample minutes
        if meeting["minutes_url"]:
            minutes_text = f"""--- Page 1 ---
SAN FRANCISCO BOARD OF SUPERVISORS
MEETING MINUTES

{meeting["date"]}

Meeting called to order at 2:05 PM by President Aaron Peskin.

ROLL CALL
Present: Supervisors Peskin, Chan, Dorsey, Engardio, Mandelman, 
Melgar, Preston, Ronen, Safai, Stefani, Walton

--- Page 2 ---

APPROVAL OF MINUTES
Minutes from the October 7, 2025 meeting were approved unanimously.

CONSENT CALENDAR
The following items were approved on consent:

• File No. 250{i}01 - ADOPTED: Resolution authorizing $2.5M budget allocation 
  for Mission District community center renovation.

• File No. 250{i}02 - PASSED: Ordinance amending height limits in SoMa district.

• File No. 250{i}03 - APPROVED: 10-year lease agreement for property at 
  567 Valencia Street for affordable artist housing.

--- Page 3 ---

REGULAR AGENDA

File No. 250{i}10 - Affordable Housing Development
Public hearing held regarding proposed 200-unit affordable housing development 
at 1234 Mission Street. 

Discussion points:
- Developer presented plans for 100% affordable units
- Community members raised concerns about parking and traffic
- Supervisor Preston moved to approve with modifications
- Vote: 8 ayes, 3 noes - APPROVED WITH CONDITIONS

--- Page 4 ---

File No. 250{i}11 - Budget and Finance Committee Report
Committee recommends approval of Q4 budget adjustments totaling $15.3M.
Key allocations:
- Public safety: $8.2M
- Homeless services: $4.5M
- Parks and recreation: $2.6M

Vote: APPROVED UNANIMOUSLY

File No. 250{i}12 - Public Safety Funding
Discussion on additional funding for community safety programs.
Deferred to next meeting for further review.

ADJOURNMENT
Meeting adjourned at 5:45 PM.
"""
            
            # Save text file
            text_path = text_dir / f"{date_safe}_minutes.txt"
            with open(text_path, 'w') as f:
                f.write(minutes_text)
            
            # Save metadata
            metadata = {
                "doc_type": "minutes",
                "url": meeting["minutes_url"],
                "meeting_date": meeting["date"],
                "original_path": f"data/sfbos_meetings_demo/raw/{date_safe}_minutes.pdf",
                "text_path": str(text_path),
                "scraped_at": datetime.now().isoformat()
            }
            
            metadata_path = metadata_dir / f"{date_safe}_minutes.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✓ Generated {date_safe}_minutes.txt")
    
    # Create a summary file
    summary = {
        "scraper": "SF Board of Supervisors Meetings",
        "demo_mode": True,
        "total_documents": len([f for f in text_dir.glob("*.txt")]),
        "output_directory": str(base_dir.absolute()),
        "structure": {
            "raw/": "Original PDF documents (simulated)",
            "text/": "Converted text files",
            "metadata/": "JSON metadata for each document"
        },
        "generated_at": datetime.now().isoformat()
    }
    
    summary_path = base_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Demo Output Generated!")
    print("=" * 60)
    print(f"Location: {base_dir.absolute()}")
    print(f"Documents created: {summary['total_documents']}")
    print("\nDirectory structure:")
    print("  raw/        - Original PDF files (simulated)")
    print("  text/       - Extracted text content")
    print("  metadata/   - Document metadata (JSON)")
    print("\nYou can now:")
    print("1. Load this data into PostgreSQL using the schema.sql")
    print("2. Build search indices")
    print("3. Extract entities (addresses, names, file numbers)")
    print("4. Create the MCP server to expose this data")
    print("=" * 60)

if __name__ == "__main__":
    create_demo_output()
