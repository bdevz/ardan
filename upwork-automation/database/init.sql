-- Upwork Automation Database Schema
-- Initialize database with core tables for jobs, proposals, applications, and system configuration

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Job status enum
CREATE TYPE job_status AS ENUM ('discovered', 'filtered', 'queued', 'applied', 'rejected', 'archived');

-- Job type enum
CREATE TYPE job_type AS ENUM ('fixed', 'hourly');

-- Proposal status enum
CREATE TYPE proposal_status AS ENUM ('draft', 'submitted', 'accepted', 'rejected');

-- Application status enum
CREATE TYPE application_status AS ENUM ('pending', 'submitted', 'viewed', 'interview', 'hired', 'declined');

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upwork_job_id VARCHAR(255) UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    budget_min DECIMAL(10,2),
    budget_max DECIMAL(10,2),
    hourly_rate DECIMAL(10,2),
    client_name VARCHAR(255),
    client_rating DECIMAL(3,2),
    client_payment_verified BOOLEAN DEFAULT false,
    client_hire_rate DECIMAL(3,2),
    posted_date TIMESTAMP WITH TIME ZONE,
    deadline TIMESTAMP WITH TIME ZONE,
    skills_required TEXT[],
    job_type job_type,
    location VARCHAR(255),
    status job_status DEFAULT 'discovered',
    match_score DECIMAL(3,2),
    match_reasons TEXT[],
    content_hash VARCHAR(64),
    job_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Proposals table
CREATE TABLE proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    bid_amount DECIMAL(10,2) NOT NULL,
    attachments TEXT[], -- Google Drive file IDs
    google_doc_url TEXT,
    google_doc_id VARCHAR(255),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    status proposal_status DEFAULT 'draft',
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Applications table
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
    upwork_application_id VARCHAR(255),
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status application_status DEFAULT 'pending',
    client_response TEXT,
    client_response_date TIMESTAMP WITH TIME ZONE,
    interview_scheduled BOOLEAN DEFAULT false,
    interview_date TIMESTAMP WITH TIME ZONE,
    hired BOOLEAN DEFAULT false,
    hire_date TIMESTAMP WITH TIME ZONE,
    session_recording_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System configuration table (single row configuration)
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    daily_application_limit INTEGER DEFAULT 30,
    min_hourly_rate DECIMAL(10,2) DEFAULT 50.0,
    target_hourly_rate DECIMAL(10,2) DEFAULT 75.0,
    min_client_rating DECIMAL(3,2) DEFAULT 4.0,
    min_hire_rate DECIMAL(3,2) DEFAULT 0.5,
    keywords_include TEXT[],
    keywords_exclude TEXT[],
    automation_enabled BOOLEAN DEFAULT true,
    notification_channels TEXT[],
    profile_name VARCHAR(255) DEFAULT 'Salesforce Agentforce Developer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Browser sessions table
CREATE TABLE browser_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    browserbase_session_id VARCHAR(255) UNIQUE NOT NULL,
    session_type VARCHAR(100) NOT NULL, -- 'job_discovery', 'proposal_submission', 'profile_management'
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'expired', 'terminated'
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance metrics table
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_type VARCHAR(100) NOT NULL, -- 'application_success', 'response_rate', 'hire_rate'
    metric_value DECIMAL(10,4) NOT NULL,
    time_period VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly'
    date_recorded DATE NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task queue table
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(100) NOT NULL,
    task_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 0,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_posted_date ON jobs(posted_date DESC);
CREATE INDEX idx_jobs_match_score ON jobs(match_score DESC);
CREATE INDEX idx_jobs_content_hash ON jobs(content_hash);
CREATE INDEX idx_proposals_job_id ON proposals(job_id);
CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_browser_sessions_type ON browser_sessions(session_type);
CREATE INDEX idx_browser_sessions_status ON browser_sessions(status);
CREATE INDEX idx_task_queue_status ON task_queue(status);
CREATE INDEX idx_task_queue_scheduled ON task_queue(scheduled_at);
CREATE INDEX idx_performance_metrics_type_date ON performance_metrics(metric_type, date_recorded);

-- Insert default system configuration
INSERT INTO system_config (
    daily_application_limit,
    min_hourly_rate,
    target_hourly_rate,
    min_client_rating,
    min_hire_rate,
    keywords_include,
    keywords_exclude,
    automation_enabled,
    notification_channels,
    profile_name
) VALUES (
    30,
    50.0,
    75.0,
    4.0,
    0.5,
    ARRAY['Salesforce', 'Agentforce', 'Salesforce AI', 'Einstein', 'Salesforce Developer'],
    ARRAY['WordPress', 'Shopify', 'PHP', 'Junior', 'Intern'],
    true,
    ARRAY['slack'],
    'Salesforce Agentforce Developer'
);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposals_updated_at BEFORE UPDATE ON proposals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_browser_sessions_updated_at BEFORE UPDATE ON browser_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();