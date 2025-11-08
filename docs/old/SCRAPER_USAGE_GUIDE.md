# Generic Scraper Framework - Usage Guide

## Overview

The new scraper framework provides a reusable base class (`BaseDataSourceScraper`) that handles:
- ✅ **Incremental scraping** - Only fetches new documents
- ✅ **State management** - Tracks what's been scraped
- ✅ **Deduplication** - Automatic via document IDs
- ✅ **Generic interface** - Easy to extend for new data sources
- ✅ **Error handling** - Robust retry and logging
- ✅ **Statistics tracking** - Know what succeeded/failed

## Quick Start

### 1. Run the SF Board of Supervisors Scraper

```bash
# First run - scrapes everything
python sfbos_scraper_v2.py --limit 5

# Second run - only new documents
python sfbos_scraper_v2.py --limit 10
# Output: "5 already scraped, 5 new documents to process"

# Force re-scrape everything
python sfbos_scraper_v2.py --force

# Reset state (clear history)
python sfbos_scraper_v2.py --reset
```

### 2. Run the Building Permits Scraper (Example)

```bash
# Scrape 100 most recent permits
python building_permits_scraper.py --limit 100

# Run again - only new permits
python building_permits_scraper.py --limit 100
```

## How Incremental Scraping Works

### State Management

Each scraper maintains a state file at `.state/scraper_state.json`:

```json
{
  "scraped_ids": [
    "abc123def456",
    "789ghi012jkl"
  ],
  "last_updated": "2025-11-08T18:45:00"
}
```

### Document IDs

Documents are uniquely identified by hashing:
- URL
- Document type
- Date

Example:
```python
doc_id = hash("https://sfbos.org/agenda/2025/bag102825" + "agenda" + "October 28, 2025")
# Result: "abc123def456"
```

This ensures:
- Same document = same ID
- No duplicates even across runs
- Updates detected by date/URL changes

### Scraping Flow

```
Run 1: Discover 10 docs → Process 10 → Save state [10 IDs]
Run 2: Discover 15 docs → Skip 10 (already scraped) → Process 5 new → Save state [15 IDs]
Run 3: Discover 15 docs → Skip 15 (nothing new) → Done
```

## Creating a New Scraper

### Step 1: Extend BaseDataSourceScraper

```python
from base_scraper import BaseDataSourceScraper, Document

class MyDataSourceScraper(BaseDataSourceScraper):
    def __init__(self, output_dir: str = "data/my_source"):
        super().__init__(output_dir, "My Data Source Name")
        # Your initialization here
```

### Step 2: Implement Required Methods

#### discover_documents()
Find all available documents to scrape:

```python
def discover_documents(self) -> List[Document]:
    documents = []
    
    # Fetch listings from API/website
    response = requests.get("https://api.example.com/documents")
    listings = response.json()
    
    # Convert to Document objects
    for listing in listings:
        doc = Document(
            doc_id=Document.generate_id(listing['url'], listing['type'], listing['date']),
            doc_type=listing['type'],
            url=listing['url'],
            date=listing['date'],
            metadata={'extra': 'info'}
        )
        documents.append(doc)
    
    return documents
```

#### download_document()
Download the document:

```python
def download_document(self, doc: Document) -> bool:
    try:
        response = requests.get(doc.url)
        filename = f"{doc.date}_{doc.doc_type}.pdf"
        path = self.raw_dir / filename
        
        with open(path, 'wb') as f:
            f.write(response.content)
        
        doc.original_path = path
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
```

#### extract_text()
Extract text from the document:

```python
def extract_text(self, doc: Document) -> str:
    # For PDFs
    with pdfplumber.open(doc.original_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)
    return text
    
    # For JSON/API data
    with open(doc.original_path) as f:
        data = json.load(f)
    return format_json_as_text(data)
    
    # For HTML
    soup = BeautifulSoup(doc.original_path.read_text(), 'html.parser')
    return soup.get_text()
```

### Step 3: Add Main Entry Point

```python
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()
    
    scraper = MyDataSourceScraper()
    
    if args.reset:
        scraper.reset_state()
        return
    
    scraper.scrape(limit=args.limit, force=args.force)

if __name__ == "__main__":
    main()
```

## Output Structure

Each scraper creates this directory structure:

```
data/my_source/
├── raw/                    # Original documents (PDFs, JSON, etc.)
│   ├── 2025-10-28_agenda.pdf
│   └── 2025-10-21_minutes.pdf
├── text/                   # Extracted text
│   ├── abc123def456.txt
│   └── 789ghi012jkl.txt
├── metadata/               # Document metadata
│   ├── abc123def456.json
│   └── 789ghi012jkl.json
└── .state/                 # Scraper state (internal)
    └── scraper_state.json
```

### Metadata Format

Each document's metadata includes:

```json
{
  "doc_id": "abc123def456",
  "doc_type": "agenda",
  "url": "https://...",
  "date": "October 28, 2025",
  "metadata": {
    "meeting_date": "October 28, 2025",
    "source": "SF Board of Supervisors"
  },
  "original_path": "data/sfbos_meetings/raw/October-28-2025_agenda.pdf",
  "text_path": "data/sfbos_meetings/text/abc123def456.txt",
  "scraped_at": "2025-11-08T18:45:00"
}
```

## Command-Line Arguments

All scrapers support these standard arguments:

```bash
--limit N          # Process only N documents
--force            # Re-scrape existing documents
--reset            # Clear state, start fresh
--output PATH      # Custom output directory
```

## Use Cases

### Daily Automated Updates

```bash
#!/bin/bash
# Run nightly to catch new documents

# Board meetings
python sfbos_scraper_v2.py

# Building permits
python building_permits_scraper.py --limit 1000

# Campaign finance
python campaign_finance_scraper.py
```

### Backfill Historical Data

```bash
# Get everything from the beginning
python sfbos_scraper_v2.py --reset
python sfbos_scraper_v2.py
```

### Development/Testing

```bash
# Test with just 5 documents
python sfbos_scraper_v2.py --limit 5

# Re-test the same documents
python sfbos_scraper_v2.py --limit 5 --force
```

## Advanced Features

### Custom State Location

```python
class MyCustomScraper(BaseDataSourceScraper):
    def __init__(self, output_dir):
        super().__init__(output_dir, "My Scraper")
        # State file is at: {output_dir}/.state/scraper_state.json
```

### Processing Statistics

The scraper tracks:
- `total_found` - Documents discovered
- `new_documents` - Successfully processed
- `skipped_existing` - Already scraped
- `failed` - Errors during processing

Access via `scraper.stats` after `scrape()`.

### Error Handling

Built-in error handling:
- Failed downloads don't block other documents
- Text extraction errors are logged
- State is saved even if some documents fail

## Examples of Different Source Types

### PDF Documents (Board Meetings)
```python
# Already implemented in sfbos_scraper_v2.py
- Download PDFs
- Extract with pdfplumber
- Save as text
```

### JSON APIs (Building Permits)
```python
# Already implemented in building_permits_scraper.py
- Query API
- Save JSON
- Convert to readable text
```

### HTML Pages (News Articles)
```python
def extract_text(self, doc: Document) -> str:
    soup = BeautifulSoup(doc.original_path.read_text(), 'html.parser')
    
    # Extract article content
    article = soup.find('article')
    title = article.find('h1').get_text()
    content = article.find('div', class_='content').get_text()
    
    return f"{title}\n\n{content}"
```

### CSV Files (Budget Data)
```python
def extract_text(self, doc: Document) -> str:
    import csv
    
    with open(doc.original_path) as f:
        reader = csv.DictReader(f)
        lines = []
        for row in reader:
            lines.append(
                f"{row['Department']}: ${row['Amount']} - {row['Description']}"
            )
    
    return "\n".join(lines)
```

## Troubleshooting

### "Nothing new to scrape"
- Normal if no new documents since last run
- Use `--force` to re-scrape
- Use `--reset` to clear state and start fresh

### State file corrupted
```bash
python your_scraper.py --reset
```

### Re-scrape specific documents
Delete their IDs from `.state/scraper_state.json` or use `--force`.

### Change document ID generation
If URLs change but documents are the same, customize `Document.generate_id()`:

```python
# Include only stable parts in ID
doc_id = Document.generate_id(
    stable_part_of_url,
    doc_type,
    date
)
```

## Integration with Database

After scraping, load into PostgreSQL:

```python
import json
from pathlib import Path

def load_documents_to_db(scraper_output_dir):
    metadata_dir = Path(scraper_output_dir) / "metadata"
    
    for meta_file in metadata_dir.glob("*.json"):
        with open(meta_file) as f:
            doc_meta = json.load(f)
        
        # Read text content
        text_path = Path(doc_meta['text_path'])
        text_content = text_path.read_text()
        
        # Insert into database
        cursor.execute("""
            INSERT INTO documents (
                doc_id, doc_type, url, date, 
                text_content, metadata, scraped_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_id) DO NOTHING
        """, (
            doc_meta['doc_id'],
            doc_meta['doc_type'],
            doc_meta['url'],
            doc_meta['date'],
            text_content,
            json.dumps(doc_meta['metadata']),
            doc_meta['scraped_at']
        ))
```

## Best Practices

### 1. Run Incrementally
```bash
# Good: Run daily, only new documents
0 2 * * * /usr/bin/python /path/to/scraper.py

# Bad: Reset state every time
0 2 * * * /usr/bin/python /path/to/scraper.py --reset && /usr/bin/python /path/to/scraper.py
```

### 2. Rate Limiting
Add delays in `download_document()`:
```python
import time
time.sleep(1)  # Be nice to servers
```

### 3. Error Notifications
```python
try:
    scraper.scrape()
except Exception as e:
    send_alert(f"Scraper failed: {e}")
    raise
```

### 4. Monitoring
```python
results = scraper.scrape()
if scraper.stats['failed'] > 0:
    logger.warning(f"{scraper.stats['failed']} documents failed")
```

## Summary

The generic scraper framework provides:

✅ **Reusable base class** - Write less boilerplate  
✅ **Incremental updates** - Only fetch what's new  
✅ **Automatic deduplication** - No manual tracking  
✅ **Consistent structure** - Same output format  
✅ **Error resilience** - One failure doesn't stop everything  
✅ **Easy extension** - 3 methods to implement  

Perfect for building a multi-source civic data platform!
