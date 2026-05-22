-- JobHunter Pro - Supabase Schema
-- Run this in your Supabase SQL Editor

-- ================================================
-- USER PROFILES TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id TEXT PRIMARY KEY DEFAULT 'default',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    location TEXT,
    headline TEXT,
    bio TEXT,
    cv_url TEXT,
    portfolio_url TEXT,
    github_url TEXT,
    linkedin_url TEXT,
    social_links JSONB DEFAULT '[]'::jsonb,
    skills TEXT[],
    experience TEXT,
    education TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see/edit their own profile
CREATE POLICY "Users can manage own profile" ON public.user_profiles
    FOR ALL USING (auth.uid() = user_id);

-- ================================================
-- JOBS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.jobs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    url TEXT UNIQUE,
    source TEXT DEFAULT 'manual',
    description TEXT,
    requirements TEXT,
    salary TEXT,
    company_rating TEXT,
    posted_date TEXT,
    status TEXT DEFAULT 'new',
    match_score REAL DEFAULT 0,
    is_live BOOLEAN DEFAULT TRUE,
    scrape_mode TEXT DEFAULT 'live',
    scraped_at TEXT,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own jobs
CREATE POLICY "Users can manage own jobs" ON public.jobs
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- ================================================
-- CONTACTS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.contacts (
    id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT NOT NULL UNIQUE,
    company TEXT,
    role TEXT,
    linkedin_url TEXT,
    source TEXT DEFAULT 'manual',
    notes TEXT,
    sent_emails INTEGER DEFAULT 0,
    last_contact TEXT,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own contacts
CREATE POLICY "Users can manage own contacts" ON public.contacts
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- ================================================
-- APPLICATIONS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES public.jobs(id) ON DELETE SET NULL,
    company TEXT NOT NULL,
    position TEXT NOT NULL,
    applied_date TEXT,
    status TEXT DEFAULT 'applied',
    follow_up_date TEXT,
    notes TEXT,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own applications
CREATE POLICY "Users can manage own applications" ON public.applications
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- ================================================
-- EMAILS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.emails (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES public.contacts(id) ON DELETE SET NULL,
    subject TEXT,
    body TEXT,
    template_used TEXT,
    sent_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'sent',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Enable RLS
ALTER TABLE public.emails ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own emails
CREATE POLICY "Users can manage own emails" ON public.emails
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- ================================================
-- METRICS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.metrics (
    id SERIAL PRIMARY KEY,
    date TEXT UNIQUE NOT NULL,
    jobs_viewed INTEGER DEFAULT 0,
    jobs_saved INTEGER DEFAULT 0,
    applications_sent INTEGER DEFAULT 0,
    responses_received INTEGER DEFAULT 0,
    interviews_scheduled INTEGER DEFAULT 0,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Enable RLS
ALTER TABLE public.metrics ENABLE ROW LEVEL SECURITY;

-- Policy: Users can manage their own metrics
CREATE POLICY "Users can manage own metrics" ON public.metrics
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- ================================================
-- DOCUMENTS TABLE
-- ================================================
CREATE TABLE IF NOT EXISTS public.documents (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_url TEXT,
    file_size INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own documents" ON public.documents
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- Create a private or public Supabase Storage bucket named:
-- jobhunter-documents
-- Then set SUPABASE_STORAGE_BUCKET=jobhunter-documents in Vercel.

-- ================================================
-- COMPATIBILITY MIGRATIONS FOR EXISTING PROJECTS
-- ================================================
ALTER TABLE public.user_profiles ALTER COLUMN id TYPE TEXT USING id::text;
ALTER TABLE public.user_profiles ALTER COLUMN id SET DEFAULT 'default';
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS social_links JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS is_live BOOLEAN DEFAULT TRUE;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS scrape_mode TEXT DEFAULT 'live';
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS scraped_at TEXT;
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS file_url TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'jobs_url_unique' AND conrelid = 'public.jobs'::regclass
    ) THEN
        ALTER TABLE public.jobs ADD CONSTRAINT jobs_url_unique UNIQUE (url);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'contacts_email_unique' AND conrelid = 'public.contacts'::regclass
    ) THEN
        ALTER TABLE public.contacts ADD CONSTRAINT contacts_email_unique UNIQUE (email);
    END IF;
END $$;

-- ================================================
-- INSERT SAMPLE DATA (Optional)
-- ================================================
INSERT INTO public.jobs (title, company, location, url, source, description, salary, status) VALUES
('Full Stack Developer', 'TechCorp', 'Remote', 'https://example.com/job1', 'linkedin', 'We are looking for a skilled Full Stack Developer to join our team...', '$80,000 - $120,000', 'new'),
('Python Engineer', 'DataFlow Inc', 'San Francisco, CA', 'https://example.com/job2', 'indeed', 'Join our engineering team to build scalable data pipelines...', '$100,000 - $140,000', 'new'),
('Frontend Developer', 'WebLabs', 'Remote', 'https://example.com/job3', 'remotive', 'We need a React expert to build beautiful user interfaces...', '$70,000 - $100,000', 'applied');

INSERT INTO public.contacts (name, email, company, role, source) VALUES
('Sarah Johnson', 'sarah.j@techcorp.com', 'TechCorp', 'Senior Recruiter', 'linkedin'),
('Mike Chen', 'mike.c@dataflow.io', 'DataFlow Inc', 'Hiring Manager', 'indeed'),
('Emily Davis', 'emily.d@weblabs.com', 'WebLabs', 'HR Director', 'manual');

INSERT INTO public.applications (company, position, status, applied_date) VALUES
('TechCorp', 'Full Stack Developer', 'interview', '2025-05-15'),
('WebLabs', 'Frontend Developer', 'applied', '2025-05-18');

-- ================================================
-- FUNCTION: Update timestamp
-- ================================================
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for user_profiles
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();
