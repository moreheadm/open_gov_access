# System Architecture Diagram

## Data Flow

```mermaid
graph TB
    subgraph "Data Sources"
        BOS[SF BOS Website<br/>sfbos.org]
        OTHER[Other Sources<br/>Future]
    end
    
    subgraph "Scraping Layer"
        BASE[Base Scraper<br/>Abstract Class]
        SFBOS[SF BOS Scraper<br/>Implementation]
        STATE[Scraper State<br/>Incremental Tracking]
        
        BASE -.-> SFBOS
        SFBOS --> STATE
    end
    
    subgraph "ETL Pipeline"
        PDF[PDF Processor<br/>pdfplumber]
        MD[Markdown Converter]
        PARSER[Vote Parser<br/>Extract Items & Votes]
        
        PDF --> MD
        MD --> PARSER
    end
    
    subgraph "Database Layer"
        DB[(PostgreSQL)]
        MODELS[SQLAlchemy Models<br/>Meeting, Document,<br/>Supervisor, Item, Vote]
        
        MODELS --> DB
    end
    
    subgraph "API Layer"
        FASTAPI[FastAPI Server]
        ENDPOINTS[REST Endpoints<br/>/api/supervisors<br/>/api/items<br/>/api/votes]
        
        FASTAPI --> ENDPOINTS
    end
    
    subgraph "Clients"
        WEB[Web Frontend]
        MCP[MCP Server]
        JOURNALIST[Journalists]
    end
    
    BOS --> SFBOS
    OTHER -.-> BASE
    SFBOS --> PDF
    PARSER --> MODELS
    DB --> FASTAPI
    ENDPOINTS --> WEB
    ENDPOINTS --> MCP
    ENDPOINTS --> JOURNALIST
    
    style BOS fill:#e1f5ff
    style DB fill:#ffe1e1
    style FASTAPI fill:#e1ffe1
    style SFBOS fill:#fff4e1
```

## Component Architecture

```mermaid
graph LR
    subgraph "backend/"
        subgraph "scrapers/"
            BASE_PY[base.py<br/>Scraper<br/>DocumentMetadata<br/>ScraperState]
            SFBOS_PY[sfbos.py<br/>SFBOSScraper]
        end
        
        subgraph "etl/"
            PIPELINE[pipeline.py<br/>ETLPipeline<br/>VoteParser]
        end
        
        subgraph "models/"
            DATABASE[database.py<br/>Meeting<br/>Document<br/>Supervisor<br/>Item<br/>Vote]
        end
        
        subgraph "api/"
            API_MAIN[main.py<br/>FastAPI App<br/>Endpoints]
        end
        
        CONFIG[config.py<br/>Settings]
        MAIN[main.py<br/>CLI]
    end
    
    BASE_PY --> SFBOS_PY
    SFBOS_PY --> PIPELINE
    PIPELINE --> DATABASE
    DATABASE --> API_MAIN
    CONFIG --> MAIN
    MAIN --> SFBOS_PY
    MAIN --> PIPELINE
    MAIN --> API_MAIN
```

## Database Schema

```mermaid
erDiagram
    MEETING ||--o{ DOCUMENT : has
    MEETING ||--o{ ITEM : contains
    ITEM ||--o{ VOTE : receives
    SUPERVISOR ||--o{ VOTE : casts
    
    MEETING {
        int id PK
        datetime meeting_date UK
        enum meeting_type
        datetime created_at
        datetime updated_at
    }
    
    DOCUMENT {
        int id PK
        string doc_id UK
        int meeting_id FK
        string source
        enum doc_type
        string url
        text raw_content
        text markdown_content
        datetime created_at
        datetime updated_at
    }
    
    SUPERVISOR {
        int id PK
        string name
        int district
        bool is_active
        datetime start_date
        datetime end_date
        datetime created_at
        datetime updated_at
    }
    
    ITEM {
        int id PK
        int meeting_id FK
        string file_number
        text title
        text description
        enum result
        int vote_count_aye
        int vote_count_no
        int vote_count_abstain
        int vote_count_absent
        int vote_count_excused
        datetime created_at
        datetime updated_at
    }
    
    VOTE {
        int id PK
        int item_id FK
        int supervisor_id FK
        enum vote
        datetime created_at
    }
```

## API Endpoints

```mermaid
graph TD
    API[FastAPI Server<br/>:8000]
    
    API --> SUP[/api/supervisors]
    API --> ITEMS[/api/items]
    API --> MEET[/api/meetings]
    API --> STATS[/api/stats]
    
    SUP --> SUP_LIST[GET /<br/>List all supervisors]
    SUP --> SUP_GET[GET /{id}<br/>Get supervisor details]
    SUP --> SUP_VOTES[GET /{id}/votes<br/>Get voting history]
    SUP --> SUP_STATS[GET /{id}/stats<br/>Get statistics]
    
    ITEMS --> ITEMS_LIST[GET /<br/>List items<br/>?search=query]
    ITEMS --> ITEMS_GET[GET /{id}<br/>Get item with votes]
    
    MEET --> MEET_LIST[GET /<br/>List meetings]
    
    STATS --> STATS_OVER[GET /overview<br/>System statistics]
```

## Scraping Flow

```mermaid
sequenceDiagram
    participant CLI
    participant Scraper
    participant State
    participant Web
    participant ETL
    participant DB
    
    CLI->>Scraper: scrape(limit=5)
    Scraper->>Web: discover()
    Web-->>Scraper: List[DocumentMetadata]
    
    Scraper->>State: filter already scraped
    State-->>Scraper: New documents only
    
    loop For each document
        Scraper->>Web: fetch(doc_meta)
        Web-->>Scraper: ScrapedDocument
        Scraper->>State: mark_scraped(doc_id)
        
        Scraper->>ETL: process_document(doc)
        ETL->>ETL: pdf_to_text()
        ETL->>ETL: pdf_to_markdown()
        ETL->>ETL: extract_items()
        ETL->>ETL: extract_votes()
        ETL->>DB: save all data
    end
    
    Scraper-->>CLI: List[ScrapedDocument]
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        subgraph "Application Server"
            API[FastAPI<br/>Uvicorn]
            WORKER[Background Worker<br/>Scraping Cron]
        end
        
        subgraph "Database"
            PG[(PostgreSQL<br/>Primary)]
            REPLICA[(PostgreSQL<br/>Replica)]
        end
        
        subgraph "Reverse Proxy"
            NGINX[Nginx]
        end
        
        subgraph "Storage"
            S3[S3/Object Storage<br/>PDF Archive]
        end
    end
    
    CLIENT[Clients] --> NGINX
    NGINX --> API
    API --> PG
    PG --> REPLICA
    WORKER --> PG
    WORKER --> S3
    
    style API fill:#e1ffe1
    style PG fill:#ffe1e1
    style NGINX fill:#e1f5ff
```

