-- Supabase Database Schema for Referral MVP
-- Multi-tenant architecture with customer-specific data isolation

-- Enable Row Level Security (RLS)
ALTER DATABASE postgres SET "app.jwt_secret" TO 'your-jwt-secret';

-- ========================================
-- CORE TABLES (Shared across all customers)
-- ========================================

-- Company Industry Tags (Global reference data)
CREATE TABLE company_industry_tags (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) UNIQUE NOT NULL,
    industry_tags JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Role Enrichment (Global reference data)
CREATE TABLE role_enrichment (
    id SERIAL PRIMARY KEY,
    role_key VARCHAR(255) UNIQUE NOT NULL,
    skills JSONB NOT NULL,
    platforms JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Title Aliases (Global reference data)
CREATE TABLE title_aliases (
    id SERIAL PRIMARY KEY,
    alias_title VARCHAR(255) UNIQUE NOT NULL,
    canonical_role VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- TENANT-SPECIFIC TABLES
-- ========================================

-- Organizations (Customers)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    max_contacts INTEGER DEFAULT 1000,
    
    -- Anonymous mode settings
    enable_anonymous_mode BOOLEAN DEFAULT false,
    default_anonymous_settings JSONB DEFAULT '{"hide_names": true, "hide_companies": false, "hide_emails": true, "generate_pseudonyms": true}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users (belong to organizations)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user', -- user, admin, owner
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, email)
);

-- Contacts (belong to organizations)
CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    uploaded_by UUID REFERENCES users(id),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255),
    company VARCHAR(255),
    position VARCHAR(500),
    linkedin_url TEXT,
    connected_on DATE,
    
    -- Tagged data
    role_tag VARCHAR(255),
    function_tag VARCHAR(255),
    seniority_tag VARCHAR(100),
    skills_tag JSONB,
    platforms_tag JSONB,
    company_industry_tags JSONB,
    
    -- Anonymous mode data
    anonymous_id VARCHAR(50) UNIQUE, -- e.g., "RedditUser_ABC123"
    anonymous_name VARCHAR(255), -- e.g., "Senior_Engineer_42"
    is_anonymous BOOLEAN DEFAULT false,
    
    -- Metadata
    source_filename VARCHAR(255),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- REFERRAL MANAGEMENT TABLES
-- ========================================

-- Job Descriptions (belong to organizations)
CREATE TABLE job_descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Extracted data
    detected_role VARCHAR(255),
    role_confidence DECIMAL(3,2),
    suggested_roles JSONB,
    extracted_skills JSONB,
    extracted_platforms JSONB,
    detected_seniority VARCHAR(100),
    
    -- Preferences
    preferred_companies JSONB,
    preferred_industries JSONB,
    
    -- Anonymous mode settings
    use_anonymous_mode BOOLEAN DEFAULT false,
    anonymous_display_settings JSONB, -- {"hide_names": true, "hide_companies": false, "hide_emails": true}
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Referral Requests
CREATE TABLE referral_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    job_description_id UUID REFERENCES job_descriptions(id) ON DELETE CASCADE,
    requested_by UUID REFERENCES users(id),
    contact_ids JSONB NOT NULL, -- Array of contact UUIDs
    status VARCHAR(50) DEFAULT 'pending', -- pending, accepted, declined, completed
    notes TEXT,
    user_notified BOOLEAN DEFAULT false,
    notified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- CUSTOMER-SPECIFIC CUSTOMIZATION TABLES
-- ========================================

-- Custom Company Tags (per organization)
CREATE TABLE custom_company_tags (
    id SERIAL PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    custom_tags JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, company_name)
);

-- Custom Role Definitions (per organization)
CREATE TABLE custom_role_definitions (
    id SERIAL PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role_name VARCHAR(255) NOT NULL,
    custom_skills JSONB,
    custom_platforms JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, role_name)
);

-- Custom Title Aliases (per organization)
CREATE TABLE custom_title_aliases (
    id SERIAL PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    alias_title VARCHAR(255) NOT NULL,
    canonical_role VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, alias_title)
);

-- ========================================
-- ANALYTICS & TRACKING TABLES
-- ========================================

-- Contact Import Sessions
CREATE TABLE import_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    total_contacts INTEGER NOT NULL,
    successful_imports INTEGER NOT NULL,
    failed_imports INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    status VARCHAR(50) DEFAULT 'processing', -- processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Job Matching Sessions
CREATE TABLE matching_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    job_description_id UUID REFERENCES job_descriptions(id),
    total_candidates INTEGER NOT NULL,
    processing_time_ms INTEGER,
    top_candidates_returned INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Contacts indexes
CREATE INDEX idx_contacts_organization ON contacts(organization_id);
CREATE INDEX idx_contacts_role_tag ON contacts(role_tag);
CREATE INDEX idx_contacts_company ON contacts(company);
CREATE INDEX idx_contacts_skills ON contacts USING GIN(skills_tag);
CREATE INDEX idx_contacts_platforms ON contacts USING GIN(platforms_tag);

-- Job descriptions indexes
CREATE INDEX idx_job_descriptions_organization ON job_descriptions(organization_id);
CREATE INDEX idx_job_descriptions_detected_role ON job_descriptions(detected_role);

-- Referral requests indexes
CREATE INDEX idx_referral_requests_organization ON referral_requests(organization_id);
CREATE INDEX idx_referral_requests_status ON referral_requests(status);

-- Users indexes
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);

-- ========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ========================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_company_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_role_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_title_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE matching_sessions ENABLE ROW LEVEL SECURITY;

-- Organization policies (users can only access their own organization)
CREATE POLICY "Users can view own organization" ON organizations
    FOR SELECT USING (auth.jwt() ->> 'organization_id' = id::text);

CREATE POLICY "Users can update own organization" ON organizations
    FOR UPDATE USING (auth.jwt() ->> 'organization_id' = id::text);

-- User policies
CREATE POLICY "Users can view organization users" ON users
    FOR SELECT USING (organization_id::text = auth.jwt() ->> 'organization_id');

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (id::text = auth.jwt() ->> 'user_id');

-- Contact policies
CREATE POLICY "Users can view organization contacts" ON contacts
    FOR SELECT USING (organization_id::text = auth.jwt() ->> 'organization_id');

CREATE POLICY "Users can insert organization contacts" ON contacts
    FOR INSERT WITH CHECK (organization_id::text = auth.jwt() ->> 'organization_id');

CREATE POLICY "Users can update organization contacts" ON contacts
    FOR UPDATE USING (organization_id::text = auth.jwt() ->> 'organization_id');

-- Job description policies
CREATE POLICY "Users can view organization jobs" ON job_descriptions
    FOR SELECT USING (organization_id::text = auth.jwt() ->> 'organization_id');

CREATE POLICY "Users can insert organization jobs" ON job_descriptions
    FOR INSERT WITH CHECK (organization_id::text = auth.jwt() ->> 'organization_id');

-- Referral request policies
CREATE POLICY "Users can view organization referrals" ON referral_requests
    FOR SELECT USING (organization_id::text = auth.jwt() ->> 'organization_id');

CREATE POLICY "Users can insert organization referrals" ON referral_requests
    FOR INSERT WITH CHECK (organization_id::text = auth.jwt() ->> 'organization_id');

-- Custom data policies
CREATE POLICY "Users can view organization custom data" ON custom_company_tags
    FOR SELECT USING (organization_id::text = auth.jwt() ->> 'organization_id');

CREATE POLICY "Users can manage organization custom data" ON custom_company_tags
    FOR ALL USING (organization_id::text = auth.jwt() ->> 'organization_id');

-- ========================================
-- FUNCTIONS AND TRIGGERS
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_descriptions_updated_at BEFORE UPDATE ON job_descriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_referral_requests_updated_at BEFORE UPDATE ON referral_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- SAMPLE DATA INSERTION
-- ========================================

-- Insert sample company industry tags
INSERT INTO company_industry_tags (company_name, industry_tags) VALUES
('salesforce', '["crm", "sales tech", "enterprise saas"]'),
('stripe', '["fintech", "payment tech", "b2b saas"]'),
('zendesk', '["customer service", "support tech", "saas"]'),
('hubspot', '["marketing", "crm", "saas"]'),
('slack', '["communication", "collaboration", "saas"]');

-- Insert sample role enrichment
INSERT INTO role_enrichment (role_key, skills, platforms) VALUES
('any:software engineer', '["python", "javascript", "react", "aws", "docker"]', '["github", "jira", "slack", "vscode"]'),
('any:account executive', '["sales", "negotiation", "crm", "prospecting"]', '["salesforce", "hubspot", "linkedin", "zoom"]'),
('any:customer success manager', '["customer success", "account management", "product adoption"]', '["gainsight", "intercom", "zendesk", "slack"]');

-- Insert sample title aliases
INSERT INTO title_aliases (alias_title, canonical_role) VALUES
('software engineer', 'software engineer'),
('senior software engineer', 'software engineer'),
('full stack developer', 'software engineer'),
('account executive', 'account executive'),
('sales representative', 'account executive');
