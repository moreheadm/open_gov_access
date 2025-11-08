# Mission Local Civic Data Platform - System Architecture

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│  • SF Board of Supervisors Meetings (Agendas & Minutes)         │
│  • Building Permits                                              │
│  • Campaign Finance Filings                                      │
│  • Business Registrations                                        │
│  • Police Reports                                                │
│  • Property Tax Data                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INGESTION LAYER (Python)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Scrapers   │  │   Parsers    │  │  Validators  │          │
│  │  (Requests,  │─▶│ (pdfplumber, │─▶│              │          │
│  │BeautifulSoup)│  │   PyPDF2)    │  │ Data Quality │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   PostgreSQL    │  │ Object Storage  │  │   Vector DB     │ │
│  │                 │  │                 │  │                 │ │
│  │ • Documents     │  │ • Original PDFs │  │ • Embeddings    │ │
│  │ • Entities      │  │ • Raw files     │  │ • Semantic      │ │
│  │ • Relationships │  │                 │  │   Search        │ │
│  │ • Patterns      │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │Entity Extract│  │Pattern Detect│  │  Indexing    │          │
│  │ (NER, NLP)   │  │  (ML/Rules)  │  │ (Full-Text)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   REST API   │  │  MCP Server  │  │  WebSocket   │          │
│  │   (FastAPI)  │  │ (AI Access)  │  │ (Real-time)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Web Frontend │  │ Claude + MCP │  │    Alerts    │          │
│  │  (React/Vue) │  │  (Direct AI) │  │(Email/Webhook)│         │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## Key User Flows

### Flow 1: Document Ingestion
```
New PDF Posted → Scraper Detects → Downloads → Converts to Text 
→ Extracts Entities → Stores in DB → Indexes for Search → Triggers Alerts
```

### Flow 2: Journalist Query (via Web)
```
Journalist Searches "1234 Mission Street" → REST API → PostgreSQL Query 
→ Returns All Documents + Entities → Display with Source Links
```

### Flow 3: AI-Powered Query (via MCP)
```
"Claude, find all board votes about affordable housing in Mission District"
→ MCP Server → Search Documents + Extract Patterns 
→ Synthesize Answer → Cite Sources
```

### Flow 4: Real-time Alert
```
New Document Scraped → Entity Extraction → Matches Alert Rule 
→ WebSocket Notification → Journalist Receives Alert → Opens Document
```

## Technology Stack

### Backend
- **Python 3.12+**
- **PostgreSQL 15+** with pgvector extension
- **FastAPI** for REST API
- **MCP SDK** for AI integration
- **Redis** for caching/queues

### Data Processing
- **BeautifulSoup4** - HTML parsing
- **pdfplumber** - PDF extraction
- **spaCy** - Named Entity Recognition
- **scikit-learn** - Pattern detection

### Storage
- **PostgreSQL** - Structured data
- **MinIO/S3** - Object storage
- **Qdrant/Pinecone** - Vector database (optional)

### Frontend
- **React/Next.js** - Web interface
- **TailwindCSS** - Styling
- **Recharts** - Data visualization

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local development
- **GitHub Actions** - CI/CD

## Database Schema Overview

```
┌─────────────────┐
│  data_sources   │
│  (registries)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐        ┌─────────────────┐
│   documents     │◀──────▶│    entities     │
│  (agendas,mins) │        │ (addr,people,   │
└────────┬────────┘        │  orgs,projects) │
         │                 └─────────────────┘
         │
         ▼
┌─────────────────┐
│document_entities│
│  (relationships)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐        ┌─────────────────┐
│detected_patterns│        │     alerts      │
│ (anomalies,     │        │  (user configs) │
│  clusters)      │        └─────────────────┘
└─────────────────┘
```

## Core Features

### 1. Multi-Source Data Integration
- Scrape from 10+ civic data sources
- Standardized format across all sources
- Automatic deduplication
- Source attribution and linking

### 2. Intelligent Search
- **Full-text**: Fast keyword search
- **Semantic**: "Find documents about housing crisis"
- **Entity-based**: "All mentions of [address]"
- **Cross-reference**: Link related documents

### 3. Entity Recognition
- Addresses (with normalization)
- People (officials, developers)
- Organizations (companies, nonprofits)
- Projects (developments, initiatives)
- File numbers (legislative tracking)

### 4. Pattern Detection
- Spending anomalies
- Voting patterns
- Geographic clusters (complaints, permits)
- Timeline correlations
- Network relationships

### 5. Real-time Monitoring
- Configurable alerts
- New document notifications
- Pattern detection triggers
- Webhook integrations

### 6. AI-Native Design
- MCP server for direct Claude access
- Natural language queries
- Automated summarization
- Context-aware results

## What Makes This Special

### Innovation
1. **Real-time civic journalism** - Breaks stories faster
2. **AI-first architecture** - Natural language as interface
3. **Pattern detection** - Find hidden connections
4. **Multi-source synthesis** - Complete picture
5. **Open source** - Reusable by any newsroom

### Impact for Mission Local
- ⏱️ **Time savings**: 80%+ reduction in research time
- 🎯 **Story discovery**: Automated anomaly detection
- 🔍 **Deep investigation**: Cross-reference all sources
- ⚡ **Real-time alerts**: Never miss important filings
- 🤖 **AI assistance**: Claude as research partner

## Next Phase Development

### Phase 1: Foundation (Weeks 1-2)
- ✅ Board meetings scraper
- ✅ Database schema
- ✅ Basic MCP server
- ⏳ Add 2-3 more data sources
- ⏳ Entity extraction pipeline

### Phase 2: Intelligence (Weeks 3-4)
- ⏳ Pattern detection algorithms
- ⏳ Cross-source correlation
- ⏳ Anomaly detection
- ⏳ Alert system

### Phase 3: Interface (Weeks 5-6)
- ⏳ Web frontend
- ⏳ Advanced search UI
- ⏳ Visualization dashboard
- ⏳ User management

### Phase 4: Production (Weeks 7-8)
- ⏳ Performance optimization
- ⏳ Error handling & monitoring
- ⏳ Documentation
- ⏳ Deployment to cloud

---

Built for Mission Local's hackathon challenge  
Goal: Supercharge civic accountability journalism with AI and automation
