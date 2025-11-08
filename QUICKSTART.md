# Quick Start Guide

Get up and running with the SF Board of Supervisors Voting Records system in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker (for PostgreSQL) OR PostgreSQL installed locally
- [uv](https://github.com/astral-sh/uv) (recommended)

## Step 1: Clone and Install

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

## Step 2: Start PostgreSQL

### Option A: Using Docker (Recommended)

```bash
docker-compose up -d
```

This starts PostgreSQL on port 5432 with:
- Username: `postgres`
- Password: `postgres`
- Database: `supervisor_votes`

### Option B: Using Local PostgreSQL

```bash
createdb supervisor_votes
export DATABASE_URL="postgresql://your_user:your_password@localhost:5432/supervisor_votes"
```

## Step 3: Initialize Database

```bash
python backend/main.py init
```

Expected output:
```
Initializing database...
✓ Database created
✓ Seeded 11 supervisors
✓ Database initialized
```

## Step 4: Scrape and Process Data

```bash
# Scrape and process 5 most recent meetings
python backend/main.py run --limit 5
```

This will:
1. Discover meeting documents from sfbos.org
2. Download PDFs
3. Convert to text/markdown
4. Extract voting records
5. Load into database

Expected output:
```
[sfbos] Discovering documents...
[sfbos] Found 5 documents
[sfbos] 5 new documents to scrape
[sfbos] Fetching 1/5: https://...
...
✓ ETL complete
```

## Step 5: Start the API

```bash
python backend/main.py serve
```

Expected output:
```
Starting API server on http://0.0.0.0:8000
Docs available at http://0.0.0.0:8000/docs
```

## Step 6: Test the API

Open your browser to:
- **API Docs**: http://localhost:8000/docs
- **Root**: http://localhost:8000

Or use curl:

```bash
# Get all supervisors
curl http://localhost:8000/api/supervisors

# Get overview statistics
curl http://localhost:8000/api/stats/overview

# Get voting items
curl http://localhost:8000/api/items?limit=10

# Get supervisor voting stats
curl http://localhost:8000/api/supervisors/1/stats
```

## Common Commands

### View Database Statistics

```bash
python backend/main.py stats
```

### Scrape More Data

```bash
# Scrape 20 meetings
python backend/main.py run --limit 20

# Full scrape (all available)
python backend/main.py run --full
```

### Reset and Start Fresh

```bash
# Reset scraper state
python backend/main.py reset

# Drop and recreate database
docker-compose down -v
docker-compose up -d
python backend/main.py init
python backend/main.py run --limit 5
```

### Development Mode

```bash
# Start API with auto-reload
python backend/main.py serve --reload
```

## Troubleshooting

### "Connection refused" to PostgreSQL

Make sure PostgreSQL is running:
```bash
docker-compose ps
```

### "No documents found"

The SF BOS website structure may have changed. Check:
```bash
python backend/main.py scrape --limit 1 --verbose
```

### Import errors

Make sure you're in the project root and dependencies are installed:
```bash
uv sync
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [docs/ARCHITECTURE.txt](docs/ARCHITECTURE.txt) for system design
- Explore the API at http://localhost:8000/docs
- Add new data sources by extending the `Scraper` class

## Example API Queries

### Find all votes by a supervisor

```bash
curl "http://localhost:8000/api/supervisors/1/votes?limit=50"
```

### Search for housing-related items

```bash
curl "http://localhost:8000/api/items?search=housing"
```

### Get detailed vote breakdown for an item

```bash
curl "http://localhost:8000/api/items/1"
```

### Get supervisor voting statistics

```bash
curl "http://localhost:8000/api/supervisors/1/stats"
```

Response:
```json
{
  "supervisor": {
    "id": 1,
    "name": "Connie Chan",
    "district": 1,
    "is_active": true
  },
  "total_votes": 150,
  "aye_count": 120,
  "no_count": 25,
  "abstain_count": 3,
  "absent_count": 2,
  "aye_percentage": 80.0
}
```

---

**You're all set!** 🎉

The system is now scraping, processing, and exposing SF Board of Supervisors voting records through a REST API.

