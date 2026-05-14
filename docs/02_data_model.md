-- PGVector extension (optional but recommended for semantic search)  
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. ENUMs and Types (State Machine and Categorization)  
DO $$ BEGIN  
    CREATE TYPE application_status AS ENUM (  
        'scraped',           -- Data scraped, not yet processed  
        'scored',            -- Scored by the LLM  
        'pending_approval',  -- Waiting for user approval (Web GUI/Telegram)  
        'approved',          -- Green light given for application  
        'applying',          -- Browser automation is active  
        'applied',           -- Application completed  
        'interview',         -- Interview invitation received  
        'rejected',          -- Rejected  
        'ghosted',           -- No response for a long time  
        'withdrawn',         -- User withdrew  
        'offer'              -- Offer received  
    );  
EXCEPTION  
    WHEN duplicate_object THEN null;  
END $$;

-- 2. User and CV Management  
CREATE TABLE user_profiles (  
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
    full_name TEXT NOT NULL,  
    email TEXT UNIQUE NOT NULL,  
    preferences JSONB DEFAULT '{  
        "target_roles": [],  
        "min_salary": 0,  
        "remote_preference": "hybrid",  
        "blocked_companies": []  
    }',  
    created_at TIMESTAMPTZ DEFAULT NOW()  
);

CREATE TABLE cv_documents (  
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
    profile_id UUID REFERENCES user_profiles(id),  
    version_name TEXT NOT NULL, -- e.g.: "Mobile_Focused", "Backend_AI_v2"  
    file_path TEXT NOT NULL,    -- S3 or local path  
    metadata JSONB,             -- Keywords extracted from PDF content  
    created_at TIMESTAMPTZ DEFAULT NOW()  
);

-- 3. Job Listings and Analysis Table  
CREATE TABLE job_listings (  
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
    external_id TEXT,           -- LinkedIn/Indeed ID (for duplicate checking)  
    source TEXT NOT NULL,       -- 'linkedin', 'greenhouse', 'direct'  
    title TEXT NOT NULL,  
    company_name TEXT NOT NULL,  
    location TEXT,  
    salary_raw TEXT,  
    salary_min NUMERIC,  
    salary_max NUMERIC,  
    description_text TEXT,  
    url TEXT UNIQUE NOT NULL,  
      
    -- AI Scoring  
    relevance_score INT CHECK (relevance_score BETWEEN 0 AND 100),  
    relevance_reasoning TEXT[],  
    detected_stack TEXT[],  
      
    -- Vector Data  
    embedding vector(384),      -- For local models such as bge-small or e5-small  
      
    status TEXT DEFAULT 'new',  
    created_at TIMESTAMPTZ DEFAULT NOW(),  
    updated_at TIMESTAMPTZ DEFAULT NOW()  
);

-- 4. Applications - The Central Table  
CREATE TABLE applications (  
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
    job_id UUID REFERENCES job_listings(id) ON DELETE CASCADE,  
    profile_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,  
    cv_id UUID REFERENCES cv_documents(id),

      
    -- State Machine Data  
    last_status_change TIMESTAMPTZ DEFAULT NOW(),  
    rejection_reason TEXT,  
    is_manual_entry BOOLEAN DEFAULT FALSE, -- If added manually by the user  
      
    -- Tracking & Analytics  
    applied_at TIMESTAMPTZ,  
    interview_date TIMESTAMPTZ,  
      
    -- Metadata (Which answer was given to which question, etc.)  
    application_data JSONB DEFAULT '{}',  
      
    created_at TIMESTAMPTZ DEFAULT NOW(),  
    UNIQUE(job_id, profile_id)  -- Prevent multiple applications to the same listing  
);

-- 5. Interaction and Browser Logs (Audit Trail)  
CREATE TABLE interaction_logs (  
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
    application_id UUID REFERENCES applications(id) ON DELETE CASCADE,  
    actor TEXT NOT NULL,         -- 'system', 'user', 'browser_agent', 'recruiter'  
    action_type TEXT NOT NULL,   -- 'hitl_question', 'form_filled', 'email_received'  
    content TEXT,  
    payload JSONB,               -- Error screenshot path or form data  
    created_at TIMESTAMPTZ DEFAULT NOW()  
);

-- 6. Platform Rate Limit Configuration  
CREATE TABLE platform_rate_limits (  
    platform TEXT PRIMARY KEY,       -- 'linkedin', 'greenhouse', 'lever', 'workday'  
    min_wait_seconds INT DEFAULT 120,  
    max_wait_seconds INT DEFAULT 600,  
    daily_cap INT DEFAULT 20,        -- Maximum daily applications  
    notes TEXT  
);

INSERT INTO platform_rate_limits VALUES  
    ('linkedin',   300, 900, 10, 'Aggressive bot detection, be careful'),  
    ('greenhouse',  60, 300, 50, 'ATS, minimal bot detection'),  
    ('lever',       60, 300, 50, NULL),  
    ('workday',    120, 600, 30, 'Shadow DOM, time-consuming');

CREATE TABLE user_sessions (  
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  
    profile_id UUID REFERENCES user_profiles(id),  
    platform TEXT NOT NULL,  
    encrypted_session_path TEXT NOT NULL, -- encrypted user_data_dir path  
    last_verified TIMESTAMPTZ,  
    is_active BOOLEAN DEFAULT TRUE,  
    created_at TIMESTAMPTZ DEFAULT NOW()  
);  
-- 6. Performance Indexes  
CREATE INDEX idx_job_listings_external_id ON job_listings(external_id);  
CREATE INDEX idx_job_listings_relevance ON job_listings(relevance_score);  
CREATE INDEX idx_applications_status ON applications(status);  
CREATE INDEX idx_listing_embedding ON job_listings USING ivfflat (embedding l2_ops);

-- ANALYTICS VIEW: Which CV version performs better?  
CREATE VIEW cv_performance_stats AS  
SELECT   
    cv.version_name,  
    COUNT(app.id) as total_applications,  
    COUNT(CASE WHEN app.status = 'interview' THEN 1 END) as interview_count,  
    COUNT(CASE WHEN app.status = 'rejected' THEN 1 END) as rejection_count,  
    ROUND(  
        (COUNT(CASE WHEN app.status = 'interview' THEN 1 END)::numeric /   
        NULLIF(COUNT(app.id), 0)) * 100, 2  
    ) as conversion_rate  
FROM cv_documents cv  
LEFT JOIN applications app ON cv.id = app.cv_id  
GROUP BY cv.version_name;
