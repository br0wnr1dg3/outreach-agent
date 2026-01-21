-- scripts/setup_supabase.sql
-- Supabase schema for agentic lead discovery

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Leads table (migrated from SQLite + new fields)
CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT,
  company TEXT,
  title TEXT,
  linkedin_url TEXT,

  -- Enrichment
  linkedin_posts JSONB,
  enriched_at TIMESTAMPTZ,
  enrichment_attempts INT DEFAULT 0,

  -- Email state
  status TEXT DEFAULT 'new',  -- new, active, replied, completed
  current_step INT DEFAULT 0,
  thread_id TEXT,
  last_message_id TEXT,
  email_1_subject TEXT,
  email_1_body TEXT,

  -- Agent metadata
  source TEXT DEFAULT 'import',  -- 'agent' | 'import'
  source_keyword TEXT,
  company_fit_score INT,
  company_fit_notes TEXT,
  company_embedding VECTOR(1536),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  imported_at TIMESTAMPTZ DEFAULT NOW(),
  last_sent_at TIMESTAMPTZ,
  next_send_at TIMESTAMPTZ
);

-- Companies searched (prevents re-scraping)
CREATE TABLE IF NOT EXISTS searched_companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT UNIQUE NOT NULL,
  company_name TEXT,
  source_keyword TEXT,
  fb_page_id TEXT,
  passed_gate_1 BOOLEAN,
  passed_gate_2 BOOLEAN,
  leads_found INT DEFAULT 0,
  fit_score INT,
  fit_notes TEXT,
  website_embedding VECTOR(1536),
  searched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed profiles (for vector similarity matching)
CREATE TABLE IF NOT EXISTS seed_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT UNIQUE NOT NULL,
  name TEXT,
  analysis JSONB,
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sent emails audit log
CREATE TABLE IF NOT EXISTS sent_emails (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  step INT NOT NULL,
  subject TEXT,
  body TEXT,
  gmail_message_id TEXT,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_next_send ON leads(next_send_at);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_searched_companies_domain ON searched_companies(domain);
CREATE INDEX IF NOT EXISTS idx_searched_companies_searched_at ON searched_companies(searched_at);

-- Vector indexes for similarity search (HNSW for fast approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_searched_companies_embedding ON searched_companies
  USING hnsw (website_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_seed_profiles_embedding ON seed_profiles
  USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_leads_embedding ON leads
  USING hnsw (company_embedding vector_cosine_ops);

-- Row Level Security (optional - enable if using Supabase Auth)
-- ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE searched_companies ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE seed_profiles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sent_emails ENABLE ROW LEVEL SECURITY;
