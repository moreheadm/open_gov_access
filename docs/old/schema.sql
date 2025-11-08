-- Mission Local Civic Data Platform - Database Schema
-- PostgreSQL with pgvector extension for semantic search

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- ============================================================================
-- DATA SOURCES
-- ============================================================================

CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(100), -- 'board_meetings', 'permits', 'campaign_finance', etc.
    base_url TEXT,
    scraper_config JSONB, -- Configuration for the scraper
    last_scraped_at TIMESTAMP,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_data_sources_type ON data_sources(source_type);

-- ============================================================================
-- DOCUMENTS
-- ============================================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_source_id UUID REFERENCES data_sources(id),
    
    -- Original document info
    original_url TEXT NOT NULL,
    original_filename VARCHAR(255),
    original_storage_path TEXT, -- Path to stored original file
    document_type VARCHAR(100), -- 'agenda', 'minutes', 'permit', 'filing', etc.
    
    -- Processed versions
    text_content TEXT,
    markdown_content TEXT,
    text_storage_path TEXT,
    
    -- Metadata
    document_date DATE,
    title TEXT,
    description TEXT,
    metadata JSONB, -- Flexible field for source-specific metadata
    
    -- Search & Analysis
    embedding VECTOR(1536), -- OpenAI ada-002 embeddings (or other)
    entities_extracted BOOLEAN DEFAULT false,
    
    -- Tracking
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_source ON documents(data_source_id);
CREATE INDEX idx_documents_date ON documents(document_date DESC);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_documents_text_search ON documents USING GIN (to_tsvector('english', text_content));

-- ============================================================================
-- ENTITIES
-- ============================================================================

CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL, -- 'address', 'person', 'organization', 'project', etc.
    name TEXT NOT NULL,
    normalized_name TEXT, -- Standardized version for matching
    
    -- Entity-specific data
    attributes JSONB, -- Flexible storage for entity attributes
    
    -- For addresses
    street_address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- For organizations/people
    official_name TEXT,
    aliases TEXT[], -- Alternative names
    
    -- Tracking
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    mention_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities(normalized_name);
CREATE INDEX idx_entities_location ON entities(latitude, longitude) WHERE latitude IS NOT NULL;
CREATE INDEX idx_entities_aliases ON entities USING GIN (aliases);

-- ============================================================================
-- DOCUMENT-ENTITY RELATIONSHIPS
-- ============================================================================

CREATE TABLE document_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    
    -- Context about the mention
    mention_context TEXT, -- Surrounding text
    confidence_score DECIMAL(3, 2), -- 0.00 to 1.00
    position_in_document INTEGER, -- Character offset or page number
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(document_id, entity_id, position_in_document)
);

CREATE INDEX idx_doc_entities_document ON document_entities(document_id);
CREATE INDEX idx_doc_entities_entity ON document_entities(entity_id);

-- ============================================================================
-- PATTERNS & ANOMALIES
-- ============================================================================

CREATE TABLE detected_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_type VARCHAR(100), -- 'cluster', 'spike', 'correlation', 'outlier'
    title VARCHAR(255),
    description TEXT,
    
    -- Related entities/documents
    entity_ids UUID[],
    document_ids UUID[],
    
    -- Pattern details
    severity VARCHAR(50), -- 'low', 'medium', 'high', 'critical'
    confidence_score DECIMAL(3, 2),
    statistical_data JSONB, -- Stats, counts, etc.
    
    -- Time range
    start_date DATE,
    end_date DATE,
    
    -- Review status
    reviewed BOOLEAN DEFAULT false,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    notes TEXT,
    
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_patterns_type ON detected_patterns(pattern_type);
CREATE INDEX idx_patterns_severity ON detected_patterns(severity);
CREATE INDEX idx_patterns_date ON detected_patterns(detected_at DESC);

-- ============================================================================
-- ALERTS
-- ============================================================================

CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL, -- Reference to user (external auth system)
    
    -- Alert configuration
    alert_type VARCHAR(100), -- 'entity', 'keyword', 'pattern', 'source'
    name VARCHAR(255),
    description TEXT,
    
    -- Conditions
    conditions JSONB, -- Flexible query/filter conditions
    entity_ids UUID[], -- Watch specific entities
    keywords TEXT[], -- Watch for keywords
    data_source_ids UUID[], -- Watch specific sources
    
    -- Delivery
    delivery_method VARCHAR(50), -- 'email', 'webhook', 'in_app'
    delivery_config JSONB,
    
    -- Status
    active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP,
    trigger_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_active ON alerts(active);

-- ============================================================================
-- ALERT EVENTS
-- ============================================================================

CREATE TABLE alert_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID REFERENCES alerts(id) ON DELETE CASCADE,
    
    -- What triggered it
    document_id UUID REFERENCES documents(id),
    entity_id UUID REFERENCES entities(id),
    pattern_id UUID REFERENCES detected_patterns(id),
    
    -- Event details
    trigger_reason TEXT,
    event_data JSONB,
    
    -- Delivery
    delivered BOOLEAN DEFAULT false,
    delivered_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alert_events_alert ON alert_events(alert_id);
CREATE INDEX idx_alert_events_created ON alert_events(created_at DESC);

-- ============================================================================
-- SEARCH QUERIES (For Analytics)
-- ============================================================================

CREATE TABLE search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    query_text TEXT,
    query_type VARCHAR(50), -- 'text', 'semantic', 'entity'
    filters JSONB,
    result_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_queries_user ON search_queries(user_id);
CREATE INDEX idx_search_queries_created ON search_queries(created_at DESC);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Entity with document count
CREATE VIEW entity_summary AS
SELECT 
    e.*,
    COUNT(DISTINCT de.document_id) as document_count,
    MAX(d.document_date) as latest_mention_date
FROM entities e
LEFT JOIN document_entities de ON e.id = de.entity_id
LEFT JOIN documents d ON de.document_id = d.id
GROUP BY e.id;

-- View: Recent activity
CREATE VIEW recent_activity AS
SELECT 
    'document' as activity_type,
    d.id as item_id,
    d.title as title,
    d.document_date as activity_date,
    d.created_at
FROM documents d
UNION ALL
SELECT 
    'pattern' as activity_type,
    p.id as item_id,
    p.title as title,
    p.start_date as activity_date,
    p.created_at
FROM detected_patterns p
ORDER BY created_at DESC;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables with updated_at
CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Insert SF Board of Supervisors as a data source
INSERT INTO data_sources (name, description, source_type, base_url)
VALUES (
    'SF Board of Supervisors Meetings',
    'Full board meeting agendas and minutes',
    'board_meetings',
    'https://sfbos.org/meetings/full-board-meetings'
);
