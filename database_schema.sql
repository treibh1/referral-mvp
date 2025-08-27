-- Multi-tenant Referral System Database Schema
-- This schema supports data isolation between organizations while allowing shared data

-- Organizations table (multi-tenant isolation)
CREATE TABLE IF NOT EXISTS organisations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    subscription_plan VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table (organization-specific)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user', -- 'admin', 'recruiter', 'user'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organisation_id, email)
);

-- Contacts table (universal - shared across organizations)
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    current_company VARCHAR(255),
    current_title VARCHAR(255),
    location VARCHAR(255),
    linkedin_url TEXT,
    skills TEXT, -- JSON array of skills
    industry VARCHAR(100),
    seniority_level VARCHAR(50),
    years_experience INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Employees table (organization-specific)
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    employee_id VARCHAR(100),
    department VARCHAR(100),
    manager_id INTEGER REFERENCES employees(id),
    hire_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organisation_id, contact_id)
);

-- Employee contacts (relationships between employees)
CREATE TABLE IF NOT EXISTS employee_contacts (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50), -- 'colleague', 'manager', 'direct_report', 'former_colleague'
    relationship_strength INTEGER DEFAULT 1, -- 1-5 scale
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, contact_id)
);

-- Core job roles (universal - shared across organizations)
CREATE TABLE IF NOT EXISTS core_job_roles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    industry VARCHAR(100),
    required_skills TEXT, -- JSON array
    preferred_skills TEXT, -- JSON array
    seniority_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Custom job roles (organization-specific)
CREATE TABLE IF NOT EXISTS custom_job_roles (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    required_skills TEXT, -- JSON array
    preferred_skills TEXT, -- JSON array
    seniority_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job descriptions (organization-specific)
CREATE TABLE IF NOT EXISTS job_descriptions (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    requirements TEXT, -- JSON object
    location VARCHAR(255),
    salary_range VARCHAR(100),
    role_criteria TEXT, -- JSON object for adaptive matching
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Search history (organization-specific)
CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    job_description_id INTEGER REFERENCES job_descriptions(id) ON DELETE SET NULL,
    search_query TEXT,
    results_count INTEGER,
    search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Location enrichment log
CREATE TABLE IF NOT EXISTS location_enrichment_log (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
    enrichment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN,
    location_found VARCHAR(255),
    api_used VARCHAR(50), -- 'bright_data_serp', 'linkedin_scraper'
    cost DECIMAL(10,4)
);

-- Subscriptions and billing
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    organisation_id INTEGER REFERENCES organisations(id) ON DELETE CASCADE,
    plan_name VARCHAR(50),
    status VARCHAR(50),
    current_period_start DATE,
    current_period_end DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_contacts_company ON contacts(current_company);
CREATE INDEX idx_contacts_location ON contacts(location);
CREATE INDEX idx_contacts_skills ON contacts USING GIN(skills);
CREATE INDEX idx_employees_org ON employees(organisation_id);
CREATE INDEX idx_job_descriptions_org ON job_descriptions(organisation_id);
CREATE INDEX idx_search_history_org ON search_history(organisation_id);
CREATE INDEX idx_location_enrichment_contact ON location_enrichment_log(contact_id);

-- Triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organisations_updated_at BEFORE UPDATE ON organisations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_employees_updated_at BEFORE UPDATE ON employees FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_core_job_roles_updated_at BEFORE UPDATE ON core_job_roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_custom_job_roles_updated_at BEFORE UPDATE ON custom_job_roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_job_descriptions_updated_at BEFORE UPDATE ON job_descriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

