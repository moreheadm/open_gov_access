# SF Supervisor Votes Tracker

Track how San Francisco Board of Supervisors members vote on legislation.

## Architecture

```
┌─────────────────┐
│  SF BOS Website │
│  (sfbos.org)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Scraper        │  ← Generic framework
│  (incremental)  │  ← SF BOS implementation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ETL Pipeline   │  ← PDF → Markdown
│                 │  ← Extract votes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │  ← SQLAlchemy models
│  (SQLite)       │  ← Supervisors, votes, items
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │  ← REST API
│  (port 8000)    │  ← /api/supervisors, /api/votes
└─────────────────┘
```

## Project Structure

```
supervisor-votes/
├── main.py              # CLI entry point
├── requirements.txt     # Dependencies
│
├── scrapers/
│   ├── base.py         # Abstract Scraper class
│   └── sfbos.py        # SF BOS implementation
│
├── models/
│   └── database.py     # SQLAlchemy models
│
├── etl/
│   └── pipeline.py     # ETL: PDF → Markdown → DB
│
├── api/
│   └── main.py         # FastAPI application
│
└── data/
    ├── supervisor_votes.db   # SQLite database
    └── state/                # Scraper state
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python main.py init
```

This creates the database and seeds it with current supervisors.

### 3. Run the Pipeline

```bash
# Scrape and process 5 most recent meetings
python main.py run --limit 5
```

This will:
1. Scrape meeting documents from sfbos.org
2. Convert PDFs to markdown
3. Extract voting records
4. Load into database

### 4. Start API Server

```bash
python main.py serve
```

API available at: http://localhost:8000  
Interactive docs: http://localhost:8000/docs

## CLI Commands

### Initialize
```bash
python main.py init
```

### Scrape Only
```bash
python main.py scrape --limit 10          # Scrape 10 documents
python main.py scrape --full              # Full scrape (not incremental)
python main.py scrape --save ./pdfs       # Save PDFs
```

### Process (ETL)
```bash
python main.py process --limit 5          # Process 5 documents
python main.py process --force            # Force re-process
```

### Run Full Pipeline
```bash
python main.py run --limit 10             # Scrape + process
```

### Serve API
```bash
python main.py serve                      # Start on port 8000
python main.py serve --port 3000          # Custom port
python main.py serve --reload             # Auto-reload
```

### Statistics
```bash
python main.py stats                      # Show database stats
```

### Reset
```bash
python main.py reset                      # Reset scraper state
```

## API Endpoints

### Supervisors

**Get all supervisors**
```http
GET /api/supervisors
```

**Get supervisor details**
```http
GET /api/supervisors/{id}
```

**Get supervisor's voting history**
```http
GET /api/supervisors/{id}/votes?limit=50&offset=0
```

**Get supervisor's statistics**
```http
GET /api/supervisors/{id}/stats
```

Response:
```json
{
  "supervisor": {
    "id": 1,
    "name": "Connie Chan",
    "district": 1
  },
  "total_votes": 150,
  "aye_count": 120,
  "no_count": 25,
  "abstain_count": 3,
  "absent_count": 2,
  "aye_percentage": 80.0
}
```

### Items (Legislation)

**Get voting items**
```http
GET /api/items?limit=50&search=housing
```

**Get item details with all votes**
```http
GET /api/items/{id}
```

Response:
```json
{
  "id": 123,
  "file_number": "250210",
  "title": "Affordable Housing Development at 1234 Mission Street",
  "result": "APPROVED",
  "meeting_date": "2025-10-21",
  "vote_count_aye": 8,
  "vote_count_no": 3,
  "votes": [
    {
      "supervisor": {"name": "Preston", "district": 5},
      "vote": "aye"
    },
    ...
  ]
}
```

### Meetings

**Get meetings**
```http
GET /api/meetings?limit=20
```

### Statistics

**Get overview stats**
```http
GET /api/stats/overview
```

Response:
```json
{
  "total_meetings": 45,
  "total_items": 523,
  "total_votes": 5753,
  "latest_meeting_date": "2025-10-28",
  "active_supervisors": 11
}
```

## Database Schema

### Supervisors
- `id`, `name`, `district`, `is_active`
- Track current and past supervisors

### Meetings
- `id`, `meeting_date`, `meeting_type`
- One meeting per date

### Documents
- `id`, `doc_id`, `source`, `doc_type`, `url`
- `raw_content`, `markdown_content`
- Links to meeting

### Items
- `id`, `file_number`, `title`, `description`
- `result`, vote counts
- Links to meeting

### Votes
- `id`, `item_id`, `supervisor_id`, `vote`
- Individual supervisor votes

## Features

### ✅ Generic Scraper Framework
- Abstract `Scraper` base class
- Easy to extend for new data sources
- Automatic state management

### ✅ Incremental Scraping
- Only scrapes new documents
- State persists across runs
- Force re-scrape option

### ✅ ETL Pipeline
- PDF → Text extraction (pdfplumber)
- PDF → Markdown conversion
- Voting data extraction
- Database loading (SQLAlchemy)

### ✅ REST API
- FastAPI with auto docs
- Supervisor voting records
- Item/legislation tracking
- Statistics endpoints

### ✅ Extensible
- Add new scrapers easily
- Modular architecture
- Clean separation of concerns

## Extending the System

### Add a New Data Source

1. Create new scraper in `scrapers/`:

```python
from scrapers.base import Scraper

class MySourceScraper(Scraper):
    def source_name(self):
        return "my_source"
    
    def discover(self):
        # Return list of document metadata
        pass
    
    def fetch(self, doc_meta):
        # Download document
        pass
    
    def parse(self, doc):
        # Extract structured data
        pass
```

2. Use it:

```python
scraper = MySourceScraper()
documents = scraper.scrape(limit=10)
```

### Add New API Endpoints

Edit `api/main.py`:

```python
@app.get("/api/my-endpoint")
def my_endpoint(db: Session = Depends(get_db)):
    # Your logic
    return {"data": "..."}
```

## Example Workflows

### Daily Automated Updates

```bash
#!/bin/bash
# Run daily at 2 AM

cd /path/to/supervisor-votes
python main.py run  # Scrape new documents and process
```

### Backfill Historical Data

```bash
# Reset state and process everything
python main.py reset
python main.py run --full
```

### Development Mode

```bash
# Terminal 1: Run pipeline
python main.py run --limit 5

# Terminal 2: Start API with auto-reload
python main.py serve --reload

# Terminal 3: Test API
curl http://localhost:8000/api/supervisors
```

## Voting Data Extraction

The ETL pipeline extracts voting data from meeting minutes using pattern matching:

1. **Identify items**: "File No. 250210 - Title"
2. **Extract vote counts**: "8 ayes, 3 noes"
3. **Parse individual votes**:
   - "Supervisor Preston voted aye"
   - Roll call format: "Ayes: Chan, Peskin..."
4. **Store structured data** in database

### Supported Vote Types
- `aye` - Yes vote
- `no` - No vote
- `abstain` - Abstained
- `absent` - Not present
- `excused` - Excused absence

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py", "serve", "--host", "0.0.0.0"]
```

### Environment Variables

```bash
export DATABASE_URL="postgresql://user:pass@localhost/votes"
python main.py serve
```

### Nginx Reverse Proxy

```nginx
location /api {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
}
```

## Troubleshooting

### "No documents found"
- Check network access to sfbos.org
- Verify URL patterns haven't changed
- Run with `--verbose` flag

### "Supervisor not found" during ETL
- Update supervisor names in `VoteParser.SUPERVISOR_NAMES`
- Re-seed database: `python main.py init`

### API not starting
- Check port 8000 is available
- Install uvicorn: `pip install uvicorn[standard]`
- Check database exists: `python main.py init`

## Development

### Run Tests

```bash
pytest tests/
```

### Code Style

```bash
black .
flake8 .
```

### Database Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## License

MIT License - see LICENSE file

## Credits

Built for Mission Local's hackathon challenge to improve civic data accessibility.

---

**Ready to track supervisor votes!** 🗳️

Start with: `python main.py init && python main.py run --limit 5`
