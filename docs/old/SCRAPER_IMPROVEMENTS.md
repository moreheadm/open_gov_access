# 🆕 NEW: Generic Scraper Framework with Incremental Updates

## What's New

We've added a **production-ready scraper framework** with:

✅ **Incremental scraping** - Only fetch new documents  
✅ **State management** - Automatic tracking  
✅ **Generic base class** - Easy to extend  
✅ **Deduplication** - No duplicate processing  
✅ **Better error handling** - Robust and resilient  

## Files Overview

### Core Framework
- **`base_scraper.py`** ⭐ - Generic base class for all scrapers
- **`SCRAPER_USAGE_GUIDE.md`** - Complete documentation

### Scraper Implementations
- **`sfbos_scraper_v2.py`** ⭐ - Improved BOS scraper (USE THIS)
- **`sfbos_scraper.py`** - Original version (deprecated)
- **`building_permits_scraper.py`** - Example for another data source

### Demos
- **`demo_incremental_scraping.py`** - Shows how incremental scraping works
- **`demo_scraper.py`** - Generates sample data

## Quick Comparison

### Old Scraper (sfbos_scraper.py)
```bash
python sfbos_scraper.py
# Always re-scrapes everything
# No state tracking
# ~150 lines of code
```

### New Scraper (sfbos_scraper_v2.py)
```bash
# First run - scrapes everything
python sfbos_scraper_v2.py --limit 10

# Second run - only new documents
python sfbos_scraper_v2.py --limit 20
# Output: "10 already scraped, 10 new documents"

# Force re-scrape
python sfbos_scraper_v2.py --force

# Reset state
python sfbos_scraper_v2.py --reset
```

## Quick Start

### 1. Use the New BOS Scraper

```bash
# Install dependencies (if not already installed)
pip install requests beautifulsoup4 pdfplumber --break-system-packages

# Run scraper
python sfbos_scraper_v2.py --limit 5

# Run again - it will skip already-scraped documents
python sfbos_scraper_v2.py --limit 10
```

### 2. See Incremental Scraping in Action

```bash
python demo_incremental_scraping.py
```

This interactive demo shows:
- Run 1: Process 5 documents
- Run 2: Skip all 5 (already scraped)
- Run 3: Process only 3 new documents
- Run 4: Force re-process everything

### 3. Create Your Own Scraper

See `building_permits_scraper.py` for a complete example of scraping SF OpenData API.

To create a new scraper:

```python
from base_scraper import BaseDataSourceScraper, Document

class MySourceScraper(BaseDataSourceScraper):
    def __init__(self):
        super().__init__("data/my_source", "My Source Name")
    
    def discover_documents(self) -> List[Document]:
        # Find available documents
        pass
    
    def download_document(self, doc: Document) -> bool:
        # Download the document
        pass
    
    def extract_text(self, doc: Document) -> str:
        # Extract text content
        pass
```

See [SCRAPER_USAGE_GUIDE.md](computer:///mnt/user-data/outputs/mission-local-platform/SCRAPER_USAGE_GUIDE.md) for complete documentation.

## How Incremental Scraping Works

### Document IDs
Each document gets a unique ID based on:
- URL
- Document type
- Date

```
ID = hash(url + type + date)
```

### State Tracking
Scraped document IDs are stored in `.state/scraper_state.json`:

```json
{
  "scraped_ids": ["abc123", "def456", "ghi789"],
  "last_updated": "2025-11-08T18:45:00"
}
```

### Scraping Logic
```
1. Discover all available documents
2. Check which are already scraped
3. Only process new ones
4. Update state file
```

### Example Output

**Run 1:**
```
Found 10 documents
   10 new documents to process

[1/10] Processing: October 28, 2025 - agenda
  ✓ Processed: abc123def456
...

Summary:
  Total found: 10
  New processed: 10
  Already scraped: 0
```

**Run 2:**
```
Found 15 documents
   10 already scraped
   5 new documents to process

[1/5] Processing: November 4, 2025 - agenda
  ✓ Processed: xyz789abc012
...

Summary:
  Total found: 15
  New processed: 5
  Already scraped: 10
```

## Command-Line Options

All scrapers support these flags:

```bash
--limit N          # Process only N documents
--force            # Re-scrape existing documents
--reset            # Clear state, start fresh
--output PATH      # Custom output directory
```

### Examples

```bash
# Scrape 5 most recent meetings
python sfbos_scraper_v2.py --limit 5

# Scrape all available meetings
python sfbos_scraper_v2.py

# Re-scrape everything (ignore state)
python sfbos_scraper_v2.py --force

# Start fresh (clear state)
python sfbos_scraper_v2.py --reset
python sfbos_scraper_v2.py

# Use custom output directory
python sfbos_scraper_v2.py --output /path/to/data
```

## Output Structure

```
data/sfbos_meetings/
├── raw/                      # Original PDFs
│   ├── October-28-2025_agenda.pdf
│   └── October-21-2025_minutes.pdf
├── text/                     # Extracted text (by doc_id)
│   ├── abc123def456.txt
│   └── ghi789jkl012.txt
├── metadata/                 # Document metadata
│   ├── abc123def456.json
│   └── ghi789jkl012.json
└── .state/                   # State tracking (internal)
    └── scraper_state.json
```

## Benefits for Your Hackathon

### 1. Production-Ready
- Run daily/hourly without re-scraping
- Automatic deduplication
- Handles errors gracefully

### 2. Scalable
- Add new data sources easily
- Consistent interface
- Reusable base class

### 3. Efficient
- Only processes new documents
- Saves bandwidth and time
- State persists across runs

### 4. Extensible
Example data sources you can add:

- ✅ Board meetings (done)
- ✅ Building permits (example provided)
- ⏳ Campaign finance
- ⏳ Business registrations
- ⏳ Police reports
- ⏳ Budget documents
- ⏳ Contract awards

Each takes ~100 lines of code using the base class!

## Integration with Database

After scraping, load documents into PostgreSQL:

```python
from pathlib import Path
import json
import psycopg2

def load_scraped_documents():
    conn = psycopg2.connect("dbname=civic_data")
    cursor = conn.cursor()
    
    metadata_dir = Path("data/sfbos_meetings/metadata")
    
    for meta_file in metadata_dir.glob("*.json"):
        with open(meta_file) as f:
            doc = json.load(f)
        
        # Read text content
        text_content = Path(doc['text_path']).read_text()
        
        # Insert into database
        cursor.execute("""
            INSERT INTO documents (
                doc_id, doc_type, url, date, text_content, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_id) DO NOTHING
        """, (
            doc['doc_id'],
            doc['doc_type'],
            doc['url'],
            doc['date'],
            text_content,
            json.dumps(doc['metadata'])
        ))
    
    conn.commit()
```

## Automated Daily Updates

Set up a cron job:

```bash
# /etc/cron.d/civic-data-scraper
# Run at 2 AM daily

0 2 * * * /usr/bin/python /path/to/sfbos_scraper_v2.py
0 2 * * * /usr/bin/python /path/to/building_permits_scraper.py --limit 1000
```

Only new documents will be processed each day!

## Troubleshooting

### "0 new documents to process"
- Normal if nothing new since last run
- Use `--force` to re-scrape anyway

### Reset State
```bash
python sfbos_scraper_v2.py --reset
```

### Check State File
```bash
cat data/sfbos_meetings/.state/scraper_state.json
```

### Delete Specific Document from State
Edit `.state/scraper_state.json` and remove the doc_id, or use `--force`.

## Next Steps

1. ✅ Use `sfbos_scraper_v2.py` instead of old scraper
2. ✅ Set up automated daily runs
3. ⏳ Add 2-3 more data sources using the base class
4. ⏳ Load scraped data into PostgreSQL
5. ⏳ Build search and entity extraction on top

## Documentation

- **[SCRAPER_USAGE_GUIDE.md](computer:///mnt/user-data/outputs/mission-local-platform/SCRAPER_USAGE_GUIDE.md)** - Complete guide
- **[base_scraper.py](computer:///mnt/user-data/outputs/mission-local-platform/base_scraper.py)** - Source code with docstrings
- **[building_permits_scraper.py](computer:///mnt/user-data/outputs/mission-local-platform/building_permits_scraper.py)** - Complete example

---

**Recommendation:** Use `sfbos_scraper_v2.py` for your hackathon. It's production-ready and demonstrates best practices for civic data collection.
